# deploy/ — prepared deployment artifacts (NOT activated)

Branch: `hardening/no-telemetry` (ystrem/hermes-webui)

This directory ships **ready-to-install** egress-hardening
artifacts. None of them are installed or executed by this
repo, by CI, or by `start.sh`/`bootstrap.py`. Activation is
deferred to the **Tailscale phase** and requires explicit
owner approval plus root access.

| Artifact | Path | Layer | Requires |
|----------|------|-------|----------|
| A | `systemd/hermes-webui.service.d/10-egress.conf` | cgroup-scoped `IPAddressDeny=any` + `IPAddressAllow=localhost` | systemd 257+, cgroup v2, root |
| B | `nftables/hermes-webui-egress.nft` | `meta skuid hermes` output filter: loopback accept, rest **log + drop** | nftables, root |

Why two layers: they fail differently. The systemd drop-in
follows the service unit and its children but only covers
processes launched through systemd. The nftables rule is
service-manager-independent and also covers manual
`./start.sh` runs and container entrypoints.

Current policy is **loopback only** because WebUI's sole
network dependency is the Hermes gateway on
`http://127.0.0.1:8642` (`api/gateway_chat.py:301-309`).
In the Tailscale phase, add the CGNAT range
(`100.64.0.0/10`) to both artifacts so `tailscale serve`
keeps working.

**Do not install in LAN test mode** (`HERMES_WEBUI_HOST=
0.0.0.0`): the UI must stay reachable from LAN clients.
These artifacts belong to the loopback-bind production mode.

See `docs/SECURITY.md` §4.3 for the full rationale and
`docs/NETWORK-AUDIT.md` for the raw evidence behind the
loopback-only policy.
