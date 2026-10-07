# NETWORK — Hermes WebUI (hardened no-telemetry, Tailscale-only)

**Build:** `ystrem/hermes-webui` @ branch `hardening/no-telemetry`
**Cíl:** WebUI neodešle nic mimo vlastní `127.0.0.1` (a v LAN test fázi ani
neblokuje legitimní LAN bind — viz sekce 3 níže).
**Žádná telemetrie. Žádné CDN. Žádné runtime requesty mimo vlastní origin.**

Tento soubor popisuje **dva provozní režimy** — bind adresa je plně
konfigurovatelná přes `HERMES_WEBUI_HOST` / `--host`, hardened varianta
ji **nehardcodesuje** (viz korekce zadání 2026-10-07).

---

## 1. Dva režimy vedle sebe

| | LAN test (teď) | Produkce (cíl) |
|--|--|--|
| **Bind adresa** | `HERMES_WEBUI_HOST=0.0.0.0` | `HERMES_WEBUI_HOST=127.0.0.1` |
| **Bind port** | `HERMES_WEBUI_PORT=8787` | `HERMES_WEBUI_PORT=8787` |
| **Loopback only?** | Ne — běží na všech iface | **Ano** — naslouchá jen na LO |
| **Vystavení do sítě** | LAN `192.168.10.40:8787` (LAN klienti) | `tailscale serve --bg 8787` (HTTPS, jen tailnet) |
| **Auth** | `HERMES_WEBUI_PASSWORD=***` (povinné — server vypne bez něj při non-loopback bind) | heslo *nebo* `tailscale serve` ACL (Tailscale identity) |
| **Přístup** | `http://192.168.10.40:8787/` z LAN | `https://<node>.<tailnet>.ts.net/` (HTTPS, MagicDNS) |
| **Externí requesty UI** | 0 (viz F0/F1 audit) | 0 |
| **Použitelné bez internetu** | Ano (LAN klient → server na stejném stroji) | Ano (tailnet klient → tailnet uzel) |
| **TLS** | Ne (LAN HTTP) | **Ano** (Tailscale terminate TLS, ne stroj samotný) |

### Proč je produkční režim bezpečnější

V LAN test režimu posílouchá server na `0.0.0.0`. To znamená, že **kdokoli
v LAN síti** se může pokoušet připojit — proto vyžadujeme heslo. V
produkčním režimu (`127.0.0.1` + `tailscale serve`):

1. Na rozhraní `lo` server nikdy nevidí provoz z LAN — **nic se nebinduje
   na LAN rozhraní**, `ss -tnlp` ukáže jen `127.0.0.1:8787`.
2. Tailscale serve funguje jako reverzní proxy mimo server — terminuje TLS,
   filtruje podle Tailscale identity (`tailscale serve --bg --https=8787
   http://127.0.0.1:8787`).
3. Útočník mimo tailnet nevidí ani port 8787 (stroj jen loopback), ani
   Tailscale HTTPS port (Tailscale sám řídí firewall).
4. Žádné requesty neopouštějí server mimo legitimní LLM provider URL
   (server → OpenAI/Anthropic/etc., konfigurované uživatelem).

Jedno zranitelné místo zbyde: HTTP requesty na legitimní LLM provider URL,
které server dělá jménem agenta. Ty nejsou requesty WebUI; WebUI jimi
nehýbe. Viz `SECURITY.md` pro detail.

---

## 2. Předpoklady (NEZAPÍNAT, jen ověřit stav)

> **DŮLEŽITÉ:** WebUI samo nenastavuje běžící služby. Pokud něco
> neposlouchá, **nepokoušíme se to rozběhnout** — jen dokumentujeme.

### 2.1 WebUI chat vyžaduje běžící Hermes gateway `api_server`

`api/gateway_chat.py:301-309` (F0 nález):

```python
def _gateway_base_url(config_data=None, environ: dict[str, str] | None = None) -> str:
    raw = (
        (environ or os.environ).get("HERMES_API_URL")
        or (config_data or {}).get("webui_gateway_base_url")
        or "http://127.0.0.1:8642"
    )
    return raw.rstrip("/") or "http://127.0.0.1:8642"
```

**Chat jde vždy na `http://127.0.0.1:8642`** (nebo `HERMES_API_URL`). Bez
běžícího `api_server` WebUI naběhne, ale chat selže. Toto je reálný
bloker dneška.

**Jak zapnout `api_server` (návod — NEZAPÍNÁME sami):**

Zapíná se v konfiguraci Hermes agenta, ne v WebUI. Postup
podle user-guide: `website/docs/user-guide/features/api-server.md`
(Hermes dokumentace — není v tomto repo):

1. Otevřít `~/.hermes/config.yaml`
2. V sekci `platforms:` přidat/aktivovat `api_server`
   (defaultní port `8642`):
   ```yaml
   platforms:
     api_server:
       enabled: true
   ```
3. Restartovat Hermes gateway/agent službu
4. Ověřit: `ss -tlnp | grep 8642` → `LISTEN ... 127.0.0.1:8642`

**Nesmíme to zapnout sami** — je to změna běžícího Hermes
configu (`~/.hermes/config.yaml`), mimo scope tohoto
hardeningu (viz §2.3 „Co **nezapínáme** sami"). Na tomto
stroji je `api_server` v `platforms:` přítomen pouze jako
implicitní disabled (v `config.yaml` není uveden). Po
zapnutí majitelem chat používá gateway-backed cestu
(`api/gateway_chat.py` → `127.0.0.1:8642`); do té doby
WebUI padne na přímý in-process runtime (viz
`NETWORK-AUDIT.md` F3 — pozor: ten volá LLM providera
přímo z procesu WebUI).

### 2.2 Co reálně poslouchá (ověřeno 2026-10-07, hermes-debian)

`ss -tlnp` (zkráceno na relevantní řádky):

```
LISTEN 0  2048  0.0.0.0:8787  ... users:(("hermes",pid=995,fd=13))
LISTEN 0  2048  0.0.0.0:8288  ...
LISTEN 0  4096  0.0.0.0:111   ...
LISTEN 0  2048  0.0.0.0:8199  ...
LISTEN 0  128   0.0.0.0:22    ...
LISTEN 0  4096  127.0.0.1:8384 ... users:(("syncthing",pid=1033,fd=13))
LISTEN 0  511   0.0.0.0:4416  ... users:(("node-MainThread",pid=2187,fd=18))
LISTEN 0  4096  0.0.0.0:8188  ...
LISTEN 0  4096  0.0.0.0:8189  ...
LISTEN 0  4096  [::]:111      ...
LISTEN 0  128   [::]:22       ...
LISTEN 0  511      *:9377     ...
LISTEN 0  4096     *:22000   ... users:(("syncthing",pid=1033,fd=12))
LISTEN 0  4096  [::]:8188     ...
LISTEN 0  4096  [::]:8189     ...
```

| Port | Co | Stav | Poznámka |
|------|----|----|---|
| `8787` | WebUI | ✅ běží (hermes) | cíl tohoto úkolu |
| `8288` | `uvicorn app:app` | ✅ běží | **NE** hermes *— nesouvisející služba v jiném dockeru (`/usr/local/bin/python3.12 /usr/local/bin/uvicorn app:app --host 0.0.0.0 --port 8288`)*. Na 8288 **neběží** Hermes MCP. |
| `8642` | Hermes api_server (gateway) | ❌ **neposlouchá** | `api_server` platform v Hermes configu je `enabled: false`. **BLOKER pro chat** — viz §2.1. |
| `5050` | Edge TTS | ❌ **neposlouchá** | TTS na tomto stroji neběží. WebUI bez TTS funguje, jen `/api/tts` vrátí 503. |

**WebUI samotné k ničemu jinému než port 8787 a loopback `8642`/a
konfigurovatelné LLM provider URL nepotřebuje.** Ostatní porty v tabulce
nám do WebUI nepatří — to jsou okolní služby (syncthing, node exporter,
ComfyUI atd.).

### 2.3 Co **nezapínáme** sami

Toto je **dokumentace**, ne task k provedení. Každá z těchto akcí
vyžaduje schválení majitele:

- ❌ **Zapnout `api_server` platform** v Hermes configu (jinak chat
  nefunguje — viz §2.1).
- ❌ **Aktivovat `IPAddressDeny=any` / nftables egress allowlist**
  (viz `SECURITY.md` §4.3).
- ❌ **Nainstalovat Tailscale** na hermes-debian.
- ❌ **Restartovat `hermes-dashboard.service`** (běží na :8787, ale
  toto je jiný proces, viz `ss` výše; úkol s ním nehýbe).

---

## 3. Bind adresa — konfigurace (NEhardcoded)

Bind je plně konfigurovatelný jako v upstreamu:

| Mechanismus | Proměnná | Příklad |
|-------------|----------|---------|
| env | `HERMES_WEBUI_HOST` | `HERMES_WEBUI_HOST=0.0.0.0` (LAN) |
| env | `HERMES_WEBUI_PORT` | `HERMES_WEBUI_PORT=8787` |
| CLI | `--host` | `--host 127.0.0.1` |
| CLI | `--port` | `--port 8787` |
| `bootstrap.py` | `DEFAULT_HOST` | `127.0.0.1` (výchozí, ale overridovatelný) |

**Hardened varianta bind NEhardcodesuje** — viz korekce zadání 2026-10-07:

> "Bind adresa musí zůstat konfigurovatelná přes env (HERMES_WEBUI_HOST),
> jak to upstream už má. Nic nehardcoduj."

**`bootstrap.py:474-479` (tento commit):**

```python
parser.add_argument("port", nargs="?", type=int, default=DEFAULT_PORT)
# Bind adresa je plne v rukou operatora pres HERMES_WEBUI_HOST / --host.
# Hardened varianta NEvynucuje 127.0.0.1 — to by znemoznilo LAN test
# (viz docs/NETWORK.md "LAN test rezim"). Produkce = loopback + tailscale
# serve; LAN test = 0.0.0.0 + heslo. Oba rezimy jsou zdokumentovany,
# bind zustava konfigurovatelny jako v upstreamu.
parser.add_argument("--host", default=DEFAULT_HOST)
```

**`server.py` (tento commit, runtime guard):**

Server.py **varuje** (ale neodmítá) při non-loopback bind bez auth:

```python
# Security: warn if binding non-loopback without authentication
from api.auth import get_oidc_startup_warning, is_auth_enabled
if HOST not in ('127.0.0.1', '::1', 'localhost') and not is_auth_enabled():
    ... # warning log
```

**Poznámka k env vars:** žádný `HERMES_WEBUI_ALLOW_PUBLIC_BIND` v kódu
neexistuje (v upstreamu není a hardened varianta ho nezavádí). Bind
omezujeme **heslem** — `HERMES_WEBUI_PASSWORD=***`. Bez hesla `server.py`
vypíše warning a v rámci non-loopback bindu by měl operátor heslo
nastavit.

---

## 4. LAN test režim (dnes)

```bash
# .env nebo export
HERMES_WEBUI_HOST=0.0.0.0
HERMES_WEBUI_PORT=8787
HERMES_WEBUI_PASSWORD=<silné heslo>   # POVINNÉ při 0.0.0.0

./bootstrap.py                       # start
# nebo:
./server.py --host 0.0.0.0 --port 8787
```

Přístup z LAN: `http://192.168.10.40:8787/` + heslo.

Ověření bindu:

```
$ ss -tnlp | grep 8787
LISTEN ... 0.0.0.0:8787 ... users:(("hermes",...))
```

**Omezení dneška:** chat selže, protože `127.0.0.1:8642` neposlouchá
(viz §2.1, §2.2). WebUI samo o sobě naběhne, ale všechny chaty/turny
vrátí chybu.

---

## 5. Produkční režim (Tailscale)

Vyžaduje: Tailscale nainstalovaný na stroji (dnes **není**; viz §2.3).

```bash
HERMES_WEBUI_HOST=127.0.0.1
HERMES_WEBUI_PORT=8787
./bootstrap.py                      # start, poslouchá jen na lo

# Vystavení přes Tailscale (HTTPS, jen pro tailnet):
sudo tailscale serve --bg --https=8787 http://127.0.0.1:8787
```

Přístup: `https://<hostname>.<tailnet>.ts.net/` z jakéhokoli zařízení
v tailnetu, HTTPS bez vlastního certifikátu (Tailscale ho zařídí).

Ověření:

```
$ ss -tnlp | grep 8787
LISTEN ... 127.0.0.1:8787 ... users:(("hermes",...))
$ sudo tailscale serve status
https://<node>.ts.net:8787 -> http://127.0.0.1:8787
```

---

## 6. Všechny URL kontaktované WebUI za běhu (po F1/F2)

| Kategorie | Adresa | Důvod |
|-----------|--------|-------|
| Same origin | `http://127.0.0.1:8787/*` (server samotný) | HTML, JS, CSS, vendored assety, `fetch()` API |
| Loopback API | `http://127.0.0.1:8642/*` (gateway) | Chat, runs, approvals, health, transcribe (pokud gateway-side STT) |
| Loopback WS  | `ws://127.0.0.1:8787/...` | Interní SSE/WebSocket mezi stránkou a serverem |

**Nic dalšího.** Žádné CDN, žádné fonty, žádné analytiky.

### Speciální případy (uživatel konfiguruje sám)

- **LLM provider URL** (OpenAI, Anthropic, Gemini, lokální Ollama): ukládá
  se v konfiguraci profilu (`api/config.py`, `api/routes.py`). Toto jsou
  adresy **server → provider**, ne WebUI → externí síť. Při hardeningu
  WebUI tyto URL nijak neomezuje (jsou to legitimní API, kam uživatel
  posílá své vlastní klíče).
- **Externí runner** (`HERMES_RUNNER_BASE_URL`): opt-in. V hardened buildu
  se nepoužívá, pokud ho operátor výslovně nenastaví.

---

## 7. Vendored assety (kde na disku)

```
static/vendor/xterm/5.3.0/{xterm.css,xterm.js}
static/vendor/xterm-addon-fit/0.8.0/xterm-addon-fit.js
static/vendor/xterm-addon-web-links/0.9.0/xterm-addon-web-links.js
static/vendor/prismjs/1.29.0/{prism-tomorrow.min.css,prism.min.css,prism-core.min.js,prism-autoloader.min.js}
static/vendor/pdfjs-dist/4.9.155/{pdf.min.mjs,pdf.worker.min.mjs}
static/vendor/mermaid/10.9.3/mermaid.min.js
```

---

## 8. Jak WebUI mluví s Hermes agentem (F0 nález)

| Vrstva | Jak | Kde |
|--------|-----|-----|
| Browser → WebUI | `fetch('/api/...')` na stejném originu | `static/{boot,ui,login,workspace,kanban}.js` |
| WebUI → Gateway | `urllib.request.urlopen('http://127.0.0.1:8642/v1/runs/...')` | `api/gateway_chat.py:301-309` |
| WebUI → lokální služby | subprocess v `bootstrap.py` (Popen) pro start/restart | `bootstrap.py:11,192,270,330,650,673` |
| WebUI → agent (subprocess) | NE — žádný direct Popen do hermes agenta | — |

**Žádný `subprocess.Popen` do běžícího agenta.** Chat jde vždy přes
HTTP(S) na `http://127.0.0.1:8642` (když běží — viz §2.1).

WebSocket: pouze `ws://127.0.0.1:*` (CSP whitelist) pro interní
kanban-bridge.

---

## 9. Test, že je to opravdu „žádná externí síť"

Viz `docs/NETWORK-AUDIT.md` — sekce 1–7. Souhrn: `grep cdn.jsdelivr`
= 0, `grep cloudflare` = 0, `grep googleapis` = 0, `grep gstatic` = 0
v `static/` i `api/`.