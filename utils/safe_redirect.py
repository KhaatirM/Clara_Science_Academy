"""Safe redirect helpers (prevent open redirects via Referer)."""

from __future__ import annotations

from urllib.parse import urlparse

from flask import request, url_for


def is_safe_redirect_url(url: str, *, allowed_hosts: set[str] | None = None) -> bool:
    """Return True if ``url`` is a same-host relative path or allowed host."""
    if not url:
        return False
    url = url.strip()
    if url.startswith('/') and not url.startswith('//'):
        return True
    try:
        ref = urlparse(url)
    except Exception:
        return False
    if ref.scheme not in ('http', 'https'):
        return False
    host = (ref.netloc or '').split('@')[-1].lower()
    if not host:
        return False
    if allowed_hosts is None:
        allowed_hosts = {request.host.lower()}
    host_only = host.split(':')[0]
    allowed = {h.lower().split(':')[0] for h in allowed_hosts}
    return host_only in allowed


def safe_redirect_target(fallback_endpoint: str = 'auth.dashboard', **fallback_kwargs):
    """Return a safe local URL from Referer, or ``url_for(fallback)``."""
    referrer = request.referrer
    if referrer and is_safe_redirect_url(referrer):
        return referrer
    return url_for(fallback_endpoint, **fallback_kwargs)
