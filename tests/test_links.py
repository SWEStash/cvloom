"""Tests for the shared profile-link vocabulary."""

from __future__ import annotations

import pytest

from cvloom.links import link_username, network_of, normalize_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://linkedin.com/in/jane", "LinkedIn"),
        ("https://www.linkedin.com/in/jane", "LinkedIn"),
        ("linkedin.com/in/jane", "LinkedIn"),
        ("https://github.com/jane", "GitHub"),
        ("https://GitHub.com/jane", "GitHub"),
        ("https://example.com/blog", None),
        # A lookalike host must not be mistaken for the real network.
        ("https://notgithub.com/jane", None),
        ("", None),
    ],
)
def test_network_of(url: str, expected: str | None) -> None:
    assert network_of(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://linkedin.com/in/jane", "jane"),
        ("https://www.linkedin.com/in/jane/", "jane"),
        ("https://github.com/jane", "jane"),
        # A repo URL is not a profile URL, so no handle is claimed.
        ("https://github.com/jane/project", ""),
        # LinkedIn company pages do not sit under /in/.
        ("https://linkedin.com/company/acme", ""),
        ("https://example.com/jane", ""),
    ],
)
def test_link_username(url: str, expected: str) -> None:
    assert link_username(url) == expected


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("https://github.com/jane", "http://github.com/jane"),
        ("https://github.com/jane", "https://www.github.com/jane"),
        ("https://github.com/jane", "https://github.com/jane/"),
        ("https://GitHub.com/Jane", "https://github.com/jane"),
        ("github.com/jane", "https://github.com/jane"),
    ],
)
def test_normalize_url_collapses_cosmetic_differences(a: str, b: str) -> None:
    assert normalize_url(a) == normalize_url(b)


def test_normalize_url_keeps_distinct_paths_apart() -> None:
    assert normalize_url("https://github.com/jane") != normalize_url("https://github.com/john")
