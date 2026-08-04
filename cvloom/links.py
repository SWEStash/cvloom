"""Shared vocabulary for profile links (``data/basics.yaml`` → ``links``).

Recognising which network a URL belongs to, and comparing two URLs for sameness.
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

    Accepts a scheme-less URL: ``github.com/me`` parses like ``https://github.com/me``.
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

    ``https://linkedin.com/in/jane/`` → ``jane``. Anything with extra path
    segments (a repo, a post) is not a profile URL and yields no handle.
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
    """Return a comparison key for *url*, ignoring scheme, ``www.``, case and
    any trailing slash."""
    split = urlsplit(url if "://" in url else f"//{url}")
    path = split.path.rstrip("/")
    return f"{_host(url)}{path}".lower()
