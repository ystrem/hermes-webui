# Network Audit — Hermes WebUI (raw evidence)

**Datum:** 2026-10-07
**Repozitář:** ystrem/hermes-webui (fork nesquena/hermes-webui, MIT)
**HEAD:** `94b4b23` na `master` (před zahájením hardeningu)
**Větev:** `hardening/no-telemetry`
**Pracovní stroj:** hermes-debian (192.168.10.40)
**Cíl:** oddělit WebUI od všech externích sítí kromě loopback + Tailscale

Tento soubor obsahuje **pouze surové výstupy** z auditu. Žádné shrnutí, žádné
interpretace — surový vstup/výstup příkazů, aby šel kdykoli zreprodukovat.

---

## 1. Identifikace všech externích URL v `static/`

### Příkaz

```
grep -rnoE '(src|href)="https?://[^"]+"' static/
```

### Výstup (master, 2026-10-07)

```
static/index.html:75:href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css"
static/index.html:93:href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css"
static/index.html:94:src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-core.min.js"
static/index.html:95:src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/autoloader/prism-autoloader.min.js"
static/index.html:96:src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"
static/index.html:97:src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"
static/index.html:98:src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.js"
static/index.html:1657:href="https://get-hermes.ai/"
static/index.html:1670:href="https://github.com/nesquena/hermes-webui/issues"
```

**Interpretace (ponechána v auditu, ne ve zprávě):**

* řádky 75, 93–98: externí assety načítané za běhu (xterm, prismjs)
* řádky 1657, 1670: marketingové/issue trackery (nekritické, ale jsou
  externí `<a href>`)

Dále `grep` na `pdfjs` a `mermaid` v `static/*.js` (dynamické vkládání):

```
static/ui.js:21397:      const _pdfSrc='https://cdn.jsdelivr.net/npm/pdfjs-dist@4.9.155/build/pdf.min.mjs';
static/ui.js:21398:      const _pdfWorker='https://cdn.jsdelivr.net/npm/pdfjs-dist@4.9.155/build/pdf.worker.min.mjs';
static/ui.js:21456:      script.src='https://cdn.jsdelivr.net/npm/mermaid@10.9.3/dist/mermaid.min.js';
static/boot.js:2946:    ?'https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css'
static/boot.js:2947:    :'https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css';
```

```
static/terminal.js:205:    surface.textContent='Terminal library failed to load. Check network access to cdn.jsdelivr.net.';
```

Textová chybová hláška, ne request — necháme, ale zaznamenáváme.

---

## 2. CSP a další povolené externí origin (api/)

### Příkaz

```
grep -rnE 'cdn\.|cdn\.jsdelivr|fonts\.googleapis|fonts\.gstatic|cloudflare' static/ api/
```

### Výstup (master, 2026-10-07)

```
static/index.html:75:  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" integrity="sha384-LJcOxlx9IMbNXDqJ2axpfEQKkAYbFjJfhXexLfiRJhjDU81mzgkiQq8rkV0j6dVh" crossorigin="anonymous">
static/index.html:93:  <link id="prism-theme" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css" crossorigin="anonymous">
static/index.html:94:  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-core.min.js" integrity="sha384-MXybTpajaBV0AkcBaCPT4KIvo0FzoCiWXgcihYsw4FUkEz0Pv3JGV6tk2G8vJtDc" crossorigin="anonymous" defer></script>
static/index.html:95:  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/autoloader/prism-autoloader.min.js" integrity="sha384-Uq05+JLko69eOiPr39ta9bh7kld5PKZoU+fF7g0EXTAriEollhZ+DrN8Q/Oi8J2Q" crossorigin="anonymous" defer></script>
static/index.html:96:  <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js" integrity="sha384-/nfmYPUzWMS6v2atn8hbljz7NE0EI1iGx34lJaNzyVjWGDzMv+ciUZUeJpKA3Glc" crossorigin="anonymous" defer></script>
static/index.html:97:  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js" integrity="sha384-AQLWHRKAgdTxkolJcLOg4E9rE89CPE2xMy3tIRFn08NcGKPTsELdvKomqji+DL" crossorigin="anonymous" defer></script>
static/index.html:98:  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.js" integrity="sha384-U4fBROT3kCM582gaYiNaOSQiJbXPzd9SfR1598Y7yeGSYVBzikXrNg0XyuU+mOnl" crossorigin="anonymous" defer></script>
static/ui.js:21397:      const _pdfSrc='https://cdn.jsdelivr.net/npm/pdfjs-dist@4.9.155/build/pdf.min.mjs';
static/ui.js:21398:      const _pdfWorker='https://cdn.jsdelivr.net/npm/pdfjs-dist@4.9.155/build/pdf.worker.min.mjs';
static/ui.js:21456:      script.src='https://cdn.jsdelivr.net/npm/mermaid@10.9.3/dist/mermaid.min.js';
static/terminal.js:205:    surface.textContent='Terminal library failed to load. Check network access to cdn.jsdelivr.net.';
static/boot.js:2946:    ?'https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css'
static/boot.js:2947:    :'https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css';
api/helpers.py:212:    "default-src 'self' https://*.cloudflareaccess.com; "
api/helpers.py:215:    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://static.cloudflareinsights.com blob:; "
api/helpers.py:216:    "worker-src blob: 'self' https://cdn.jsdelivr.net; "
api/helpers.py:217:    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
api/helpers.py:219:    "font-src 'self' data: https://fonts.gstatic.com; "
api/helpers.py:223:    "manifest-src 'self' https://*.cloudflareaccess.com; "
api/helpers.py:335:    return f"{_CSP_CONNECT_BASE} https://cdn.jsdelivr.net{extra_connect_src}"
```

### Kompletní CSP šablona (api/helpers.py:209-228)

```python
_CSP_SHARED_POLICY_TEMPLATE = (
    "default-src 'self' https://*.cloudflareaccess.com; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://static.cloudflareinsights.com blob:; "
    "worker-src blob: 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "img-src {img_src}; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "media-src 'self' data: blob:; "
    "connect-src {connect_src}; "
    "frame-src {frame_src}; "
    "manifest-src 'self' https://*.cloudflareaccess.com; "
    "base-uri 'self'; form-action 'self'"
)
```

**Poznámka:** `cloudflareinsights`/`cloudflareaccess` jsou **v CSP povoleny**,
ale nebyly nalezeny žádné requesty, které by je v kódu aktivovaly (žádný
`beacon()`/`fetch()` na tyto domény). Slouží to spíš jako „výchozí
povolení" pro nasazení za Cloudflare Access tunelem.

---

## 3. Telemetrie (sentry, posthog, firebase, …)

### Příkaz

```
grep -rniE '\b(sentry|posthog|firebase|gtag|google-analytics|segment\.com|mixpanel|amplitude|datadog|newrelic|bugsnag|rollbar|fullstory|hotjar|intercom|optimizely)\b' static/ api/ server.py bootstrap.py
```

### Výstup (master, 2026-10-07)

```
(prázdné — žádné externí analytické SDK)
```

### Příkaz (slovo `telemetry` pro interní UI signály)

```
grep -rnE 'telemetry' static/ api/
```

### Výstup (master, 2026-10-07)

```
static/index.html:904:        <div class="main-view-title" data-i18n="insights_title">Usage Analytics</div>
static/ui.js:1327:  // (verified via real-device telemetry: DOM collapsed to 1 row, scrollHeight
static/terminal.js:525:  // with no feedback and no telemetry. Let the browser auto-reconnect a merely
static/terminal.js:528:  // flapping connection can't flood the pane or telemetry.
static/i18n.js:1176:    insights_title: 'Usage Analytics',
static/messages.js:5226:    // LLM telemetry is usually tokens/sec, but the UI reveals words. A fixed word
api/background_process.py:31:The marker is *not* required for delivery — it's a telemetry-style flag the
api/background_process.py:1615:    ``PENDING_BG_TASK_COMPLETIONS`` telemetry marker is dropped too, so no
api/background_process.py:1691:    # The session-level PENDING marker is server-internal telemetry; the
api/models.py:2535:    auth.json is rewritten by OAuth/token-refresh and request telemetry churn.
api/models.py:5120:            # Telemetry (#1624): log legitimate repair firings so the next batch
api/run_journal.py:57:# Events that are live-UI-only telemetry with no recovery value in the run
api/run_journal.py:498:    # Live-UI-only telemetry (metering) has no recovery value in the journal:
api/run_journal.py:522:    Live-UI-only telemetry rows (see ``REPLAY_SKIPPED_SSE_EVENTS``) carry no
api/config.py:8139:    # Per-credential status/telemetry — churns on every request, not config.
api/config.py:8384:    # DEBUG telemetry per stage-294 absorption: makes "why did my cache
api/routes.py:12554:    """Return usage analytics from local WebUI session data."""
api/routes.py:24160:    telemetry flag with no payload, so re-marking alone is a no-op), then
api/routes.py:25819:    (analytics, telemetry) has a stable hook. ``PENDING_BG_TASK_COMPLETIONS`` is
```

**Interpretace:** žádný externí tracking. Všechny zásahy jsou buď
komentáře, interní „metering" pro live UI, nebo návěští
`PENDING_BG_TASK_COMPLETIONS` (server-side flag, ne request). Volání
`/api/usage/analytics` vrací **lokální** session data (server-side agregace,
ne odesílá nikam ven).

---

## 4. Python dependency tree

### Příkaz

```
cat requirements.txt
```

### Výstup

```
# Hermes Web UI -- minimal Python dependencies
# The server uses PyYAML plus cryptography for optional local passkey/WebAuthn support.
# All heavy ML/agent deps live in the Hermes agent venv.
#
# OPTIONAL: the Edge TTS speech engine (Settings -> Voice -> TTS Engine -> "Edge TTS")
# needs `edge-tts`. It is intentionally NOT a hard dependency — the /api/tts
# endpoint returns 503 with an install hint when it's absent. Install it only if
# you want server-side Microsoft neural voices:  pip install edge-tts
#
# OPTIONAL: macOS/non-procfs CPU/RAM system-health metrics need `psutil`.
# Linux uses procfs without this dependency; install only if you want aggregate
# CPU/RAM metrics on platforms without /proc:  pip install psutil>=5.9
pyyaml>=6.0
cryptography>=42.0
# OPTIONAL: Office workspace preview/edit support needs these parsers.
# The workspace file routes return 503 with an install hint when they are absent.
# Install them only if you want .docx/.xlsx/.pptx preview support:
#   pip install python-docx>=1.1.2 openpyxl>=3.1.5 python-pptx>=1.0.2
```

### requirements-dev.txt (zkráceno)

```
-r requirements.txt
pytest
pytest-timeout
pytest-asyncio
pytest-shard
ruff
mcp>=1.28,<2
python-docx
openpyxl
python-pptx
ruamel.yaml>=0.18
```

### package.json

```json
{
  "name": "hermes-webui-devtools",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "lint:runtime": "eslint --no-config-lookup -c eslint.runtime-guard.config.mjs \"static/**/*.js\""
  },
  "devDependencies": {
    "eslint": "^10.4.0"
  }
}
```

**Žádný bundler, žádný package install za běhu.** `package.json` slouží
jen pro ESLint runtime-guard lint, nic se nestahuje při startu WebUI.

---

## 5. Jak WebUI mluví s Hermes agentem (F0 cíl)

### 5.1 Chat / běhové requesty

**Soubor:** `api/gateway_chat.py:301-309`

```python
def _gateway_base_url(config_data=None, environ: dict[str, str] | None = None) -> str:
    raw = (
        (environ or os.environ).get("HERMES_API_URL")
        or (config_data or {}).get("webui_gateway_base_url")
        or "http://127.0.0.1:8642"
    )
    return raw.rstrip("/") or "http://127.0.0.1:8642"
```

**Nalezení:** Frontend (browser) → WebUI server (loopback) → `http://127.0.0.1:8642`
(Hermes Gateway chat API). Tj. **žádný subprocess spawn** pro chat. Všechno
jde HTTP/SSE přes loopback.

### 5.2 Externí runner (opt-in)

**Soubor:** `api/runner_client.py:31-58`

```python
class HttpRunnerClient:
    def __init__(self, *, base_url: str, api_key: str = ""):
        self.base_url = str(base_url or "").strip().rstrip("/")
        ...
    def from_env(cls, environ=None):
        base_url = str(source.get(_RUNNER_BASE_URL_ENV) or "").strip()
        ...
```

Runner client existuje jen pro volitelný externí runner
(`HERMES_RUNNER_BASE_URL`); pokud není nastaveno, factory vrací `None` a
runner se nepoužívá.

### 5.3 Frontend fetch() — všechny relativní

```
$ grep -rnE "fetch\(['\"]" static/ | head
static/login.js:71:      var res = await fetch('api/auth/login', {
static/login.js:112:      var optRes = await fetch('api/auth/passkey/options', { method: 'POST', body: '{}', credentials: 'include' });
static/login.js:133:      var res = await fetch('api/auth/passkey/login', {
static/login.js:149:    fetch('api/auth/status', { credentials: 'include' })
static/login.js:180:      fetch('health', { method: 'GET', credentials: 'same-origin' })
static/boot.js:928:      const res=await fetch('api/transcribe',{method:'POST',body:form});
static/boot.js:1161:      const res=await fetch('api/transcribe/capability',{cache:'no-store'});
...
```

**Všechny `fetch()` v `static/*.js` jdou na relativní URL → stejný
server (loopback).**

### 5.4 WebSocket (kanban bridge, interní UI)

**Soubor:** `api/kanban_bridge.py:1087`

```
Mirrors the agent dashboard's WebSocket /events contract event-for-event
```

CSP povoluje `ws://127.0.0.1:* ws://localhost:*` (`api/helpers.py:191`).
Žádný veřejný WebSocket.

---

## 6. Bind adresa a port (server.py + bootstrap.py)

### bootstrap.py:76-77

```python
DEFAULT_HOST = os.getenv("HERMES_WEBUI_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("HERMES_WEBUI_PORT", "8787"))
```

**Výchozí bind je `127.0.0.1:8787`.** CLI přepínač `--host` existuje, ale
v upstreamu **není defaultně nastaven na `0.0.0.0`**. V `--help`:

```
--host HOST   Bind address (default: 127.0.0.1)
--port PORT   Bind port (default: 8787)
```

### docker-compose.yml:17-20

```yaml
ports:
# select only one; use 127.0.0.1 version to expose to localhost only
  - "127.0.0.1:8787:8787"
#      - "8787:8787"
```

I v Dockeru preferuje loopback.

### Běžící proces (2026-10-07, hermes-debian)

```
root        2193    2154  1 07:20 ?        00:04:28 python3 /app/server.py
```

```
$ ss -tnlp | grep 8787
LISTEN 0      2048         0.0.0.0:8787       0.0.0.0:*    users:(("hermes",pid=995,fd=13))
```

**Kontradikce:** nasazení v Dockeru reálně běží na `0.0.0.0:8787`. To
**neodpovídá** doporučení v `docker-compose.yml`. Toto je ten reálný
problém: produkční kontejner naslouchá na všech iface, nejen loopback.

---

## 7. Souhrn externího povrchu (F0 závěr)

| Třída | Nalezení | Riziko |
|---|---|---|
| CDN runtime assety (HTML) | `index.html:75,93-98` (7× jsdelivr) | Střední — narušuje „no-telemetry" |
| CDN runtime assety (JS) | `boot.js:2946-7`, `ui.js:21397-8, 21456` | Střední — narušuje no-telemetry |
| CDN v CSP | `helpers.py:212,215,216,217,335` | Střední — CSP whitelistuje odchozí |
| Google Fonts | `helpers.py:217,219` (CSP `style-src` + `font-src`) | Nízké — jen CSS, ale porušuje pravidlo |
| Cloudflare | `helpers.py:212,215,223` (CSP) | Nízké — kód je nepoužívá, ale CSP povoluje |
| Marketing `<a href>` | `index.html:1657,1670` | Nízké — jen uživatel kliká |
| Externí telemetry SDK | **0 nálezů** | OK |
| Egress chat | `http://127.0.0.1:8642` (gateway) | OK (loopback) |
| Bind default | `127.0.0.1:8787` (kód) vs `0.0.0.0:8787` (Docker) | **Neshoda** — Docker override |
| Tailscale | nenainstalováno | Bloker pro F2 |

F0 hotov — surové vstupy/výstupy tvoří audit trail. F1/F2 navazují.
