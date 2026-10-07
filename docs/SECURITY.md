# SECURITY — Hermes WebUI (hardened no-telemetry, Tailscale-only)

**Build:** `ystrem/hermes-webui` @ branch `hardening/no-telemetry`

---

## 1. Vrstvy obrany

| Vrstva | Mechanismus | Stav po F1/F2 |
|--------|-------------|---------------|
| Bind | `HERMES_WEBUI_HOST` konfigurovatelný | ✅ výchozí `127.0.0.1`, ale overridovatelný (LAN test režim) |
| CSP | `default-src 'self'; ...` | ✅ žádné CDN, žádné fonty, žádné cloudy |
| Server egress | `urllib` v `api/agent_health.py` míří jen na gateway URL | ✅ gateway = loopback |
| Server egress | subprocess v `bootstrap.py` (restart WebUI samotného) | ✅ loopback |
| Telemetrie SDK | 0 nálezů v `static/` i `api/` | ✅ žádná |
| Vendoring | všechny runtime assety self-hostnuté | ✅ `static/vendor/<pkg>/<ver>/` |
| Auth | heslo / OIDC / passkey | ⚠ viz `api/auth.py`; non-loopback bind vyžaduje heslo |
| Egress allowlist | systemd / nftables / netns | ⏸ PŘIPRAVENO v dokumentaci, **nespuštěno** (viz §4.3) — vyžaduje sudo, aktivuje se v Tailscale fázi po schválení |

---

## 2. Bind hardening — konfigurovatelný, NEhardcoded

### 2.1 Výchozí (LAN test i produkce)

`bootstrap.py:76-77`:

```python
DEFAULT_HOST = os.getenv("HERMES_WEBUI_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("HERMES_WEBUI_PORT", "8787"))
```

Výchozí bind je loopback, ale **přes `HERMES_WEBUI_HOST` overridnutelný**
na `0.0.0.0` apod. (LAN test). Toto je záměr — viz korekce zadání
2026-10-07:

> "Bind adresa musí zůstat konfigurovatelná přes env (HERMES_WEBUI_HOST),
> jak to upstream už má. Nic nehardcoduj."

### 2.2 Runtime guard (non-loopback vyžaduje auth)

`server.py` varuje (ale **neodmítá**) při non-loopback bind bez auth:

```python
# Security: warn if binding non-loopback without authentication
from api.auth import get_oidc_startup_warning, is_auth_enabled
if HOST not in ('127.0.0.1', '::1', 'localhost') and not is_auth_enabled():
    ...  # warning log
```

Při `HERMES_WEBUI_HOST=0.0.0.0` musí operátor nastavit
`HERMES_WEBUI_PASSWORD=***` (nebo OIDC). Jinak se varování vypíše a
non-loopback bind se zachová, ale server se chrání heslem.

Tato upstream-ochrana zůstává i v tomto buildu — pass na hardened.

### 2.3 Přechod mezi režimy (viz `NETWORK.md` §1)

| Režim | Bind | Vystavení |
|-------|------|-----------|
| LAN test | `HERMES_WEBUI_HOST=0.0.0.0` | LAN klient `http://192.168.10.40:8787/` + heslo |
| Produkce | `HERMES_WEBUI_HOST=127.0.0.1` | `tailscale serve --bg` → `https://<node>.<tailnet>.ts.net/` |

Žádný kód se mezi režimy nemění — pouze env proměnná.

---

## 3. CSP hardening (po F1)

`api/helpers.py:209-225`:

```
default-src 'self';
object-src 'none';
frame-ancestors 'none';
script-src 'self' 'unsafe-inline' blob:;
worker-src blob: 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob: <extra>;
font-src 'self' data:;
media-src 'self' data: blob:;
connect-src <loopback-only> <extra>;
frame-src 'self' <extra>;
manifest-src 'self';
base-uri 'self'; form-action 'self';
```

Žádné `cdn.jsdelivr`, `fonts.googleapis.com`, `fonts.gstatic.com`,
`static.cloudflareinsights.com`, `*.cloudflareaccess.com`.

`connect-src` se skládá z `_CSP_CONNECT_BASE` (= `'self' http://127.0.0.1:* http://localhost:* http://ipc.localhost https://127.0.0.1:* https://localhost:* ws://127.0.0.1:* ws://localhost:*`) + opt-in
`HERMES_WEBUI_CSP_CONNECT_EXTRA` (pouze http(s)/ws(s) origin tvaru).

---

## 4. Doporučené nasazení (dva režimy)

### 4.1 LAN test režim (dnes)

```sh
# .env nebo export
HERMES_WEBUI_HOST=0.0.0.0
HERMES_WEBUI_PORT=8787
HERMES_WEBUI_PASSWORD=<silné heslo>   # POVINNÉ při 0.0.0.0

python3 server.py
# nebo bootstrap.py
```

Přístup: `http://192.168.10.40:8787/` z LAN klientů + heslo.

**Egress allowlist NENÍ aktivní** (viz §4.3) — UI může být dosažitelné
z LAN, a proto musí mít heslo (viz `server.py` warning).

### 4.2 Produkční režim (Tailscale — cíl)

Vyžaduje: Tailscale nainstalovaný na stroji (dnes **není**; viz
`NETWORK-AUDIT.md` F2/F3 blokery).

```sh
HERMES_WEBUI_HOST=127.0.0.1
HERMES_WEBUI_PORT=8787
python3 server.py

# Vystavení:
sudo tailscale serve --bg --https=8787 http://127.0.0.1:8787
```

Přístup: `https://<node>.<tailnet>.ts.net/` z tailnet klientů.

Produkční režim je bezpečnější, protože:

1. `ss -tnlp` ukáže jen `127.0.0.1:8787` — **nic na fyzických iface**.
2. Tailscale serve terminuje TLS, filtruje podle identity (volitelně).
3. Z internetu/cizí LAN port nevidí — Tailscale sám řídí firewall.
4. Žádné runtime requesty neopouštějí server (viz §6).

### 4.3 Egress allowlist (F2 — artefakty připraveny, **nespuštěny**)

Egress allowlist je teď **reálný artefakt v repo**, ne jen text
v docs. Oba soubory jen připravují — **neinstalují se** sami
(viz `deploy/README.md`). Aktivace je až v Tailscale fázi po
schválení majitele (korekce 2026-10-07: „připrav, ale
**nespouštěj** — na LAN fázi musí být UI dosažitelné z LAN").

| Artefakt | Soubor | Co dělá | Nasazení (root, manuálně) |
|----------|--------|---------|----------------------------|
| A | `deploy/systemd/hermes-webui.service.d/10-egress.conf` | cgroup-scoped `IPAddressDeny=any` + `IPAddressAllow=localhost` | `sudo cp` do `/etc/systemd/system/hermes-webui.service.d/`, `daemon-reload`, `restart` |
| B | `deploy/nftables/hermes-webui-egress.nft` | nftables `meta skuid hermes`: loopback accept, zbytek **log + drop** | `sudo nft -f deploy/nftables/hermes-webui-egress.nft` (rollback: `delete table`) |

**Požadavky:** systemd 257+ a cgroup v2 pro variantu A
(`systemd --version | head -1`; `stat -fc %T /sys/fs/cgroup`
→ `cgroup2fs`). Na hermes-debian podpořeno.

**Proč dvě vrstvy:** selhávají odlišně. `IPAddressDeny=` je
vázáno na systemd unit a její potomky — chrání jen procesy
spuštěné přes systemd. nftables `meta skuid` je nezávislý na
service manageru — chrání i manuální `./start.sh`, vstup do
kontejneru i proces mimo systemd. Dohromady pokrývají obě
cesty; žádná z nich není aktivní.

**Proč zatím jen `localhost`:** jediná síťová závislost WebUI
je Hermes gateway na `http://127.0.0.1:8642`
(`api/gateway_chat.py:301-309`, overridování `HERMES_API_URL`).
F0/F1 audit potvrdil, že runtime requesty jinam nejdou. V
Tailscale fázi se přidá `IPAddressAllow=100.64.0.0/10`
(systemd) resp. `ip daddr 100.64.0.0/10 accept` (nftables),
aby `tailscale serve` mohl proxovat.

**Důležité:** v LAN test režimu (`HERMES_WEBUI_HOST=0.0.0.0`)
nesmí být allowlist aktivní — UI musí být dosažitelné z LAN.
Artefakty se instaluají až při přechodu na produkční režim.

#### Starší varianty (historie, nahrazeny artefakty A/B)

Původní koncepty — Varianty A (systemd), B (nftables), C
(network namespace) — byly sloučeny do dvou připravených
artefaktů výše. Varianta C (netns) zůstává zamítnuta:
vyžaduje routing tabulky a Tailscale v ns, vyšší provozní
zátěž bez přidané ochrany proti A+B.

---

## 5. Threat model (k čemu se tohle vyplatí)

| Hrozba | Mitigation |
|--------|------------|
| Útočník vloží CDN skript přes MITM | CDN není v CSP, není v kódu → fetch CSP blokuje |
| Útočník vloří CDN skript přes XSS | `'unsafe-inline'` v `script-src` zůstává kvůli existujícím inline handlerům v UI. Doporučujeme auditovat konkrétní místa (TODO — mimo scope tohoto commitu). |
| Útočník skenuje port 8787 z LAN | V LAN režimu: heslo. V produkci: loopback bind, port není vidět z LAN. |
| Útočník skenuje port 8787 z internetu | V LAN režimu: NAT neforwarduje 8787 (default). V produkci: loopback bind + Tailscale — port vůbec neexistuje na veřejném iface. |
| Útočník na stejném stroji čte sessions | Vyžaduje heslo (HERMES_WEBUI_PASSWORD / OIDC / passkey) |
| Útočník donutí server načíst vzdálený font | font-src 'self' data: — blokováno CSP |
| Útočník podstrčí analytický skript do build pipeline | Žádný bundler, vendoring z `static/vendor/`, vizuální diff v PR |

---

## 6. Audit trail (důkazy)

Všechny změny jsou v commitu `build(vendor):` + `fix(security):` na
branchi `hardening/no-telemetry`. Viz `docs/NETWORK-AUDIT.md` pro
surové vstupy/výstupy `grep`, `cat`, `ss -tnlp`.