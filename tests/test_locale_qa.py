"""The escaped-English audit, run through a pseudo-locale.

Every string a CV template can source from the locale pack is bracketed in
``tests/fixtures/locales/qa.yaml``. Render with that pack and anything
unbracketed came from a literal in the template or the code — which is exactly
the failure mode 6.3 removes and that review cannot reliably catch across six
templates.

The pack is a fixture rather than a shipped locale: it is staged into a temp copy
of ``cvloom/locales/``, so it never reaches a wheel and never shows up in
``cvloom.locale.available_locales()``.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from cvloom import loader, locale, renderer, sections

_QA_FIXTURE = Path(__file__).parent / "fixtures" / "locales" / "qa.yaml"

_CV_TEMPLATES = [
    "cv/ats-clean",
    "cv/academic",
    "cv/modern-single",
    "cv/executive-dark",
    "cv/timeline-clean",
    "cv/sidebar-compact",
]

# Every section switched on, so every heading a template can emit is exercised.
# The work entry deliberately has no end_date: that is what makes `date_range`
# reach for the pack's `ongoing.render`.
_EVERY_SECTION_CONTEXT: dict[str, Any] = {
    "contact": {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "+1 555",
        "location": "Springfield",
    },
    "basics": {
        "headline": "Engineer",
        "summary": "Builds things.",
        "links": [{"label": "GitHub", "url": "https://github.com/jane"}],
    },
    "work": [
        {
            "company": "Acme Corp",
            "title": "Engineer",
            "start_date": "2020-01",
            "end_date": None,
            "location": "Remote",
            "highlights": ["Built things."],
        },
    ],
    "education": [
        {
            "institution": "Uni",
            "degree": "BSc",
            "field": "CS",
            "location": "Cambridge",
            "start_date": "2016",
            "end_date": "2020",
            "highlights": [],
        },
    ],
    "skills": [{"category": "Backend", "items": ["Python", "Go"]}],
    "projects": [
        {
            "name": "proj",
            "description": "A project.",
            "url": "https://example.com",
            "start_date": "2024-01",
            "highlights": [],
        },
    ],
    "publications": [
        {"name": "A paper", "publisher": "ACM", "release_date": "2023-05"},
    ],
    "certifications": [
        {"name": "CKA", "issuer": "CNCF", "date": "2023-04", "type": "certification"},
        {"name": "FP in Scala", "issuer": "Coursera", "date": "2022-09", "type": "course"},
    ],
    "awards": [{"title": "Best Poster", "awarder": "ACM", "date": "2022-06"}],
    "languages": [{"language": "Spanish", "fluency": "Native speaker"}],
    "show": dict.fromkeys(
        (
            "work",
            "education",
            "skills",
            "projects",
            "publications",
            "certifications",
            "awards",
            "languages",
        ),
        True,
    ),
    "section_order": [
        "skills",
        "work",
        "education",
        "projects",
        "publications",
        "certifications",
        "awards",
        "languages",
    ],
    "job_context": {"company": "Acme Corp", "role": "SWE", "hiring_manager": "Bob", "notes": ""},
    "profile": {},
    "section_titles": {},
    "public": False,
    "today": "March 22, 2026",
}

for _section in sections.ARRAY_SECTIONS:
    # Templates run under StrictUndefined and test schema-optional keys for
    # truthiness, so the fixture goes through the same normalization the builder
    # applies rather than spelling every optional key out here.
    loader.normalize_optional_fields(_section, _EVERY_SECTION_CONTEXT[_section])

_H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.DOTALL)


@pytest.fixture
def qa_pack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[locale.LocalePack]:
    """Stage the qa fixture beside the shipped packs and load it.

    ``load_pack`` is cached, so the cache is cleared both ways — otherwise the
    pseudo-locale would leak into the rest of the suite.
    """
    staged = tmp_path / "locales"
    shutil.copytree(locale._LOCALES_DIR, staged)
    shutil.copy(_QA_FIXTURE, staged / "qa.yaml")
    monkeypatch.setattr(locale, "_LOCALES_DIR", staged)
    locale.load_pack.cache_clear()
    pack, warnings = locale.load_pack("qa")
    assert warnings == (), f"the qa pack should be complete, but: {warnings}"
    yield pack
    locale.load_pack.cache_clear()


def _render(template: str, pack: locale.LocalePack) -> str:
    return renderer.render_template(template, dict(_EVERY_SECTION_CONTEXT), locale=pack)


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_every_heading_comes_from_the_pack(template: str, qa_pack: locale.LocalePack) -> None:
    """No <h2> may carry wording the template chose for itself.

    Every section heading in the six packaged templates is an ``<h2>``, so the
    set of ``<h2>`` texts is the complete set of headings a build can emit. An
    unbracketed one is a literal that survived — the audit's whole point.

    That equivalence is the audit's one assumption, and it is not enforced
    anywhere: a template heading a section with an ``<h3>`` or a styled ``<div>``
    would fall outside this regex and could ship a hardcoded English literal
    unnoticed. `docs/dev/custom-templates.md` states the constraint for template
    authors; widen the pattern here if a design ever needs to break it.
    """
    raw = _H2_RE.findall(_render(template, qa_pack))
    headings = [re.sub(r"<[^>]+>", "", h).strip() for h in raw]

    assert headings, f"{template} rendered no section headings at all"
    escaped = [h for h in headings if not (h.startswith("⟦") and h.endswith("⟧"))]
    assert not escaped, f"{template} renders headings the locale pack does not own: {escaped}"


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_html_lang_comes_from_the_pack(template: str, qa_pack: locale.LocalePack) -> None:
    """`<html lang>` drives WeasyPrint hyphenation and the PDF /Lang an ATS reads."""
    assert '<html lang="qa">' in _render(template, qa_pack)


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_open_ended_date_comes_from_the_pack(template: str, qa_pack: locale.LocalePack) -> None:
    """An entry with no end date renders the pack's word, not "Present"."""
    html = _render(template, qa_pack)
    assert "⟦Present⟧" in html
    assert html.count("Present") == html.count("⟦Present⟧")


def test_qa_is_not_a_shipped_locale() -> None:
    """The audit pack is test scaffolding; users must never be offered it."""
    assert "qa" not in locale.available_locales()
    assert not (locale._LOCALES_DIR / "qa.yaml").exists()
