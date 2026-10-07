"""Hardened no-telemetry: CSP must NOT allow external CDN/font origins.

Upstream previously tested *presence* of cdn.jsdelivr (xterm source maps)
and fonts.googleapis.com/gstatic in CSP. Hardened build self-hosts all
assets in static/vendor/ — these origins are now forbidden.

This test inverts the upstream assertion: the hardened CSP must
exclude the external origins that the upstream required.
"""
import re

from api.helpers import _build_csp_enforced_policy


def _policy() -> str:
    return _build_csp_enforced_policy("")


class TestHardenedCSPExcludesExternalCDN:
    """Hardened CSP must not allow cdn.jsdelivr anywhere."""

    def test_no_cdn_jsdelivr_in_any_directive(self):
        policy = _policy()
        assert "cdn.jsdelivr" not in policy, (
            "Hardened CSP must NOT include cdn.jsdelivr — all assets are "
            "vendored in static/vendor/<pkg>/<ver>/. Presence indicates "
            "a regression to the upstream CDN dependency."
        )

    def test_connect_src_has_no_jsdelivr(self):
        policy = _policy()
        connect_match = re.search(r"connect-src\s+([^;]+);", policy)
        assert connect_match, "connect-src directive must exist"
        assert "cdn.jsdelivr" not in connect_match.group(1), (
            "connect-src must not whitelist cdn.jsdelivr — xterm source "
            "maps are now served from the same origin (static/vendor/)."
        )


class TestHardenedCSPExcludesGoogleFonts:
    """Hardened CSP must not allow Google Fonts origins."""

    def test_no_fonts_googleapis_in_any_directive(self):
        policy = _policy()
        assert "fonts.googleapis.com" not in policy, (
            "Hardened CSP must NOT include fonts.googleapis.com — system "
            "fonts / vendored KaTeX are used; no Google Fonts dependency."
        )

    def test_no_fonts_gstatic_in_any_directive(self):
        policy = _policy()
        assert "fonts.gstatic.com" not in policy, (
            "Hardened CSP must NOT include fonts.gstatic.com — see above."
        )


class TestHardenedCSPExcludesCloudflare:
    """Hardened CSP must not allow Cloudflare telemetry/access origins."""

    def test_no_cloudflareinsights_in_script_src(self):
        policy = _policy()
        script_match = re.search(r"script-src\s+([^;]+);", policy)
        assert script_match, "script-src directive must exist"
        assert "cloudflareinsights" not in script_match.group(1), (
            "script-src must NOT include static.cloudflareinsights.com — "
            "the hardened variant ships no Cloudflare telemetry beacon."
        )

    def test_no_cloudflareaccess_in_default_or_manifest(self):
        policy = _policy()
        for directive_name in ("default-src", "manifest-src"):
            m = re.search(rf"{directive_name}\s+([^;]+);", policy)
            assert m, f"{directive_name} directive must exist"
            assert "cloudflareaccess" not in m.group(1), (
                f"{directive_name} must NOT include cloudflareaccess — "
                "no Cloudflare Access tunnel is used in the hardened build."
            )


class TestHardenedCSPPreservesExistingDirectives:
    """Sanity: hardened CSP keeps the upstream structural directives."""

    def test_required_directives_present(self):
        policy = _policy()
        for directive in (
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "manifest-src 'self'",
            "base-uri 'self'",
            "form-action 'self'",
        ):
            assert directive in policy, f"CSP must still contain: {directive}"