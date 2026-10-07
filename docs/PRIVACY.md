# PRIVACY — Hermes WebUI (hardened no-telemetry, Tailscale-only)

**Build:** `ystrem/hermes-webui` @ branch `hardening/no-telemetry`

## TL;DR

Server **neopouští** žádná data směrem k třetím stranám. WebUI neodesílá
žádné analytické signály, nepoužívá CDN, nenačítá vzdálené fonty. Všechna
asetová stažení probíhají ze **stejného** serveru (loopback). Bind adresa
je konfigurovatelná — výchozí `127.0.0.1`, ale LAN test režim běží na
`0.0.0.0` s heslem (viz `NETWORK.md` §1, `SECURITY.md` §4.1).

## Co **neopouští** server (za běhu)

| Typ | Proč ne |
|-----|---------|
| Telemetrie (Sentry/PostHog/Firebase/Segment/Google Analytics/Mixpanel/Amplitude/Datadog/New Relic/Bugsnag/Rollbar/FullStory/Hotjar/Intercom/Optimizely) | V kódu 0 nálezů (viz `NETWORK-AUDIT.md` §3). |
| CDN runtime assety | Vše self-hostováno v `static/vendor/`. |
| Google Fonts / jiné webfonty | Žádné `<link rel="stylesheet" href="https://fonts.googleapis.com/...">`. CSP `font-src 'self' data:`. |
| Cloudflare Insights / Cloudflare Access | V upstream CSP byly tyto domény povoleny; hardened build je **odstranil** z CSP. |
| Externí dokumentační/issue linky v UI | `<a href="https://get-hermes.ai/">` a `https://<repo>/issues` jsou v upstreamu v `index.html`. **Jedou se i v hardened buildu** (neklikne-li, nic se nestane; je to prostý HTML). WebUI je sám **neotevírá** — žádný runtime request. |
| Beacons do vzdálených origin | `navigator.sendBeacon` se používá jen pro vlastní `/api/...` (relativní URL). |
| WebSocket mimo loopback | CSP whitelistuje pouze `ws://127.0.0.1:* ws://localhost:*`. |

## Co server **může** opustit (a je to v pořádku)

1. **HTTP(S) na `127.0.0.1:8642` (Hermes gateway chat API).**
   Toto je loopback → stejný stroj, jiný proces. Žádná externí síť.
2. **HTTP(S) na adresy LLM providerů** nakonfigurované v profilu
   (OpenAI, Anthropic, Gemini, lokální Ollama, atd.).
   Toto jsou **uživatelova API**, kam posílá své vlastní klíče. WebUI
   je pouze relay. Pokud tyto URL nechcete, profil je jednoduše
   nepoužívá.
3. **Subprocess pro start/restart WebUI** (`bootstrap.py:650, 673`).
   Ten spawnuje `python3 server.py` lokálně, žádná síť.
4. **Loopback WebSocket** (kanban-bridge, agent dashboard) — viz CSP.

## Cookies, localStorage, sessionStorage

Server nastavuje session cookie (`auth.session`) — drží se v prohlížeči,
neprochází sítí mimo server. LocalStorage a sessionStorage ukládají
klientské preference (téma, jazyk, drafty). Žádné 3rd-party klíče.

## Co když provozuju na Tailscale serve?

Když `tailscale serve --bg 8787` zpřístupní port 8787 přes HTTPS s
Tailscale-IP serveru, provoz z prohlížeče na ten node jde šifrovaně
přes Tailscale (WireGuard). Žádná data neopustí Tailscale síť, pokud
se nepoužije `tailscale funnel` (ten je **veřejný** — nedoporučujeme,
viz `SECURITY.md`).

## Co když provozuju na LAN test režimu?

Bind `0.0.0.0` znamená, že server poslouchá na všech LAN rozhraních.
Server sám o sobě neodesílá nic mimo legitimní LLM provider URL
(viz sekce výše) — **LAN bind neotevíše nový outbound**. Pouze
**umožňuje dalším strojům se připojit dovnitř**. Heslo (`HERMES_WEBUI_PASSWORD`)
je nutné, jinak upstream varování v `server.py` vyzve operátora.

Rizika LAN režimu (proč produkce preferuje Tailscale):

- Kdokoli na LAN se může pokoušet připojit.
- Heslo je jediná ochrana — heslo může uniknout / být slabé.
- Neexistuje TLS (HTTP, ne HTTPS).
- Přístup je z libovolného LAN stroje bez identity kontroly.

Produkční režim (`127.0.0.1` + `tailscale serve`) eliminuje všechny
čtyři body — viz `NETWORK.md` §1.