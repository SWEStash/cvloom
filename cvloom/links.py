"""Shared vocabulary for profile links (``data/basics.yaml`` → ``links``).

Links used to live in two places — handle fields in ``private/contact.yaml`` and
labelled URLs in ``basics.public_links`` — and were reconciled at render time by
substring-matching the handle against the URL. That guard broke on a stale
handle, on ``www.`` prefixes, and on trailing slashes. ``links`` is now the
single source, so the only reconciliation left is recognising which network a
URL belongs to and comparing two URLs for sameness; both live here.
"""

from __future__ import annotations

from urllib.parse import urlsplit

# Host suffix → (canonical label, path-prefix to strip when recovering a handle).
_NETWORKS: dict[str, tuple[str, str]] = {
    "linkedin.com": ("LinkedIn", "in/"),
    "github.com": ("GitHub", ""),
}


def _host(url: str) -> str:
    """Return the lowercased host of *url*, without ``www.``.

    Falls back to parsing a scheme-less URL, since a hand-written YAML value is
    as likely to read ``github.com/me`` as ``https://github.com/me``.
    """
    parsed = urlsplit(url if "://" in url else f"//{url}")
    return parsed.netloc.lower().removeprefix("www.")


def network_of(url: str) -> str | None:
    """Return the canonical network label for *url*, or None if unrecognised."""
    host = _host(url)
    for suffix, (label, _) in _NETWORKS.items():
        if host == suffix or host.endswith(f".{suffix}"):
            return label
    return None


def link_username(url: str) -> str:
    """Recover the account handle from a known network URL, else empty string.

    ``https://linkedin.com/in/jane/`` → ``jane``; ``https://github.com/jane`` →
    ``jane``. Anything with extra path segments (a repo, a post) is not a
    profile URL, so no handle is claimed.
    """
    host = _host(url)
    for suffix, (_, prefix) in _NETWORKS.items():
        if host != suffix and not host.endswith(f".{suffix}"):
            continue
        path = urlsplit(url if "://" in url else f"//{url}").path.strip("/")
        if prefix:
            if not path.startswith(prefix):
                return ""
            path = path[len(prefix) :]
        return path if path and "/" not in path else ""
    return ""


def normalize_url(url: str) -> str:
    """Return a comparison key for *url*, ignoring cosmetic differences.

    Scheme, ``www.``, host case, and a trailing slash all vary between how a
    person types a URL and how the site reports it, and none of them change
    where the link points.
    """
    split = urlsplit(url if "://" in url else f"//{url}")
    path = split.path.rstrip("/")
    return f"{_host(url)}{path}".lower()
