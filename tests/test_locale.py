"""Tests for locale packs.

The completeness tests are the important ones: they assert ``en.yaml`` covers
everything the code looks up, derived from the code rather than from a
hand-written list, so adding a lookup without an ``en`` default fails CI.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path

import pytest

from cvloom import builder, config, linter, locale, sections
from cvloom.export import to_json_resume, to_markdown
from tests import conftest
from tests.conftest import make_project


@pytest.fixture
def packs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect pack loading at a writable copy of the shipped locales.

    ``load_pack`` is cached, so the cache is cleared on the way in and out —
    otherwise a stub written here would leak into the rest of the suite.
    """
    staged = tmp_path / "locales"
    shutil.copytree(locale._LOCALES_DIR, staged)
    monkeypatch.setattr(locale, "_LOCALES_DIR", staged)
    locale.load_pack.cache_clear()
    yield staged
    locale.load_pack.cache_clear()


# ---------------------------------------------------------------------------
# Completeness contract
# ---------------------------------------------------------------------------


def test_en_defines_every_pack_key() -> None:
    """Every LocalePack field except `code` must come from en.yaml."""
    pack, _ = locale.load_pack("en")
    for f in fields(locale.LocalePack):
        assert getattr(pack, f.name), f"en.yaml supplies no value for '{f.name}'"


def test_en_section_titles_cover_every_title_key() -> None:
    """The pack's headings track sections.TITLE_KEYS exactly.

    Derived from the registry, never restated: a new renameable section without
    an `en` heading fails here rather than rendering an empty <h2>.
    """
    pack, _ = locale.load_pack("en")
    assert set(pack.section_titles) == set(sections.TITLE_KEYS)


def test_en_ongoing_is_populated_both_ways() -> None:
    """`render` and `accepts` are one field; a pack with half of it is broken."""
    pack, _ = locale.load_pack("en")
    assert pack.ongoing.render
    assert pack.ongoing.accepts
    assert pack.ongoing.matches(pack.ongoing.render)


def test_en_matches_the_literals_it_replaced() -> None:
    """Pins en.yaml to the wording it took over from the code in 6.3.

    The constants these were compared against are gone — the pack is now the only
    place they live, so the expected values are spelled out here. Without this
    pin, editing en.yaml is a silent change to every default English build.
    """
    pack, _ = locale.load_pack("en")
    assert pack.html_lang == "en"
    assert pack.ongoing.render == "Present"
    assert dict(pack.placeholder_contact) == {
        "name": "Your Name",
        "email": "your.email@example.com",
        "phone": "+1 (555) 000-0000",
        "location": "City, Country",
    }
    assert pack.section_titles["certifications"] == "Certifications"
    assert pack.section_titles["professional_development"] == "Professional Development"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_available_locales_lists_en() -> None:
    assert "en" in locale.available_locales()


def test_en_loads_without_warnings() -> None:
    pack, warnings = locale.load_pack("en")
    assert pack.code == "en"
    assert warnings == ()


def test_unknown_locale_names_the_available_ones() -> None:
    with pytest.raises(config.ConfigError) as exc:
        locale.load_pack("zz")
    message = exc.value.errors[0]
    assert "zz" in message
    assert "en" in message


def test_missing_key_falls_back_to_en_with_a_warning(packs_dir: Path) -> None:
    (packs_dir / "xx.yaml").write_text(
        "html_lang: xx\n"
        "section_titles:\n  work: Trabajo\n"
        "ongoing:\n  render: Actualidad\n  accepts: [Actualidad]\n"
    )
    pack, warnings = locale.load_pack("xx")

    en, _ = locale.load_pack("en")
    assert pack.placeholder_contact == en.placeholder_contact
    assert any("placeholder_contact" in w and "xx" in w for w in warnings)


def test_present_keys_are_not_overridden_by_en(packs_dir: Path) -> None:
    (packs_dir / "xx.yaml").write_text(
        "html_lang: xx\n"
        "section_titles:\n  work: Trabajo\n"
        "ongoing:\n  render: Actualidad\n  accepts: [Actualidad]\n"
    )
    pack, _ = locale.load_pack("xx")
    assert pack.html_lang == "xx"
    assert pack.ongoing.render == "Actualidad"
    assert pack.ongoing.matches("actualidad")
    assert not pack.ongoing.matches("Present")


def test_half_populated_ongoing_fails_schema_validation(packs_dir: Path) -> None:
    """F7's named risk: `render` without `accepts` would silently degrade
    chronology ranking and open-ended date export."""
    (packs_dir / "xx.yaml").write_text("ongoing:\n  render: Actualidad\n")
    with pytest.raises(config.ConfigError) as exc:
        locale.load_pack("xx")
    assert any("locales/xx.yaml" in e for e in exc.value.errors)


def test_unknown_pack_key_is_rejected(packs_dir: Path) -> None:
    (packs_dir / "xx.yaml").write_text("html_langs: xx\n")
    with pytest.raises(config.ConfigError):
        locale.load_pack("xx")


def test_malformed_pack_fails_at_load_with_its_path(packs_dir: Path) -> None:
    (packs_dir / "xx.yaml").write_text("html_lang: [unclosed\n")
    with pytest.raises(config.ConfigError) as exc:
        locale.load_pack("xx")
    assert "locales/xx.yaml" in exc.value.errors[0]


def test_key_missing_from_en_is_an_error(packs_dir: Path) -> None:
    """en is the completeness contract — nothing is left to fall back to."""
    (packs_dir / "en.yaml").write_text("html_lang: en\n")
    with pytest.raises(config.ConfigError) as exc:
        locale.load_pack("en")
    assert "en.yaml" in exc.value.errors[0]
    assert "section_titles" in exc.value.errors[0]


def test_pack_mappings_are_read_only() -> None:
    """load_pack is cached, so every build shares one instance."""
    pack, _ = locale.load_pack("en")
    with pytest.raises(TypeError):
        pack.section_titles["work"] = "Mutated"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Wiring through the builder
# ---------------------------------------------------------------------------


def test_project_without_config_resolves_to_en(tmp_path: Path) -> None:
    """The invisibility contract: no cvloom.yaml behaves exactly as before."""
    root = make_project(tmp_path)
    resolved = builder.resolve_project(root, "general")
    assert resolved.locale.code == "en"
    assert resolved.warnings == []


def test_declared_locale_is_resolved(tmp_path: Path) -> None:
    root = make_project(tmp_path, extra={"cvloom.yaml": "locale: en\n"})
    assert builder.resolve_project(root, "general").locale.code == "en"


def test_unknown_locale_fails_resolution(tmp_path: Path) -> None:
    """Config problems arrive as ResolveError so every frontend already handles them."""
    root = make_project(tmp_path, extra={"cvloom.yaml": "locale: zz\n"})
    with pytest.raises(builder.ResolveError) as exc:
        builder.resolve_project(root, "general")
    assert "zz" in exc.value.errors[0]
    assert "en" in exc.value.errors[0]


def test_bad_config_key_fails_resolution(tmp_path: Path) -> None:
    root = make_project(tmp_path, extra={"cvloom.yaml": "locale: en\nlocal: es\n"})
    with pytest.raises(builder.ResolveError):
        builder.resolve_project(root, "general")


def test_build_project_reads_the_config(tmp_path: Path) -> None:
    """`build_project` reaches `resolve` directly rather than via
    `resolve_project`, so it needs its own locale wiring — it did not get it the
    first time, and `cvloom build` silently ignored cvloom.yaml."""
    root = make_project(tmp_path, extra={"cvloom.yaml": "locale: zz\n"})
    with pytest.raises(builder.ResolveError):
        builder.build_project(root, profile_name="general", public=True, skip_pdf=True)


def test_build_project_carries_the_pack_onto_the_result(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    result = builder.build_project(root, profile_name="general", public=True, skip_pdf=True)
    assert result.resolved.locale.code == "en"


def test_build_and_check_agree_on_the_locale(tmp_path: Path, packs_dir: Path) -> None:
    """The failure mode behind the bug above: one entry point resolving a pack
    the other does not see."""
    (packs_dir / "xx.yaml").write_text(
        "html_lang: xx\n"
        "section_titles:\n  work: Trabajo\n"
        "ongoing:\n  render: Actualidad\n  accepts: [Actualidad]\n"
        "placeholder_contact:\n"
        "  name: Su Nombre\n  email: tu.correo@example.com\n"
        "  phone: '+1 (555) 000-0000'\n  location: Ciudad\n"
    )
    root = make_project(tmp_path, extra={"cvloom.yaml": "locale: xx\n"})
    built = builder.build_project(root, profile_name="general", public=True, skip_pdf=True)
    resolved = builder.resolve_project(root, "general", public=True)
    assert built.resolved.locale.code == resolved.locale.code == "xx"


def test_resolve_defaults_to_en_without_a_root(tmp_path: Path) -> None:
    """`resolve` takes directories, not a root, so it cannot read cvloom.yaml."""
    root = make_project(tmp_path)
    resolved = builder.resolve(
        data_dir=root / "data",
        private_dir=root / "private",
        profiles_dir=root / "profiles",
        profile_name="general",
    )
    assert resolved.locale.code == "en"


# ---------------------------------------------------------------------------
# Consuming the pack (6.3)
# ---------------------------------------------------------------------------

_ES_PACK = (
    "html_lang: es\n"
    "section_titles:\n"
    "  work: Experiencia\n  skills: Competencias\n  education: Formación\n"
    "  projects: Proyectos\n  publications: Publicaciones\n"
    "  certifications: Certificaciones\n  awards: Premios\n  languages: Idiomas\n"
    "  summary: Perfil\n  professional_development: Formación continua\n"
    "  contact: Contacto\n"
    "ongoing:\n  render: Actualidad\n  accepts: [Actualidad]\n"
    "placeholder_contact:\n"
    "  name: Su Nombre\n  email: tu.correo@example.com\n"
    "  phone: '+1 (555) 000-0000'\n  location: Ciudad, País\n"
)

# One work entry still open, written the way a Spanish project writes it.
_ES_WORK = (
    "- company: Acme\n  title: Ingeniero\n  location: Remoto\n"
    '  start_date: "2020-01"\n  end_date: Actualidad\n'
    "  highlights:\n    - Diseñé y construí un sistema distribuido.\n"
    "- company: Globex\n  title: Ingeniero\n"
    '  start_date: "2016-01"\n  end_date: "2019-12"\n'
    "  highlights:\n    - Mantuve la plataforma de pagos.\n"
)


@pytest.fixture
def es_project(tmp_path: Path, packs_dir: Path) -> Path:
    (packs_dir / "es.yaml").write_text(_ES_PACK)
    return make_project(
        tmp_path,
        extra={"cvloom.yaml": "locale: es\n", "data/work.yaml": _ES_WORK},
    )


def test_html_lang_and_headings_follow_the_pack(es_project: Path) -> None:
    """`<html lang>` drives WeasyPrint hyphenation and the PDF /Lang an ATS reads."""
    result = builder.build_project(es_project, profile_name="general", public=True, skip_pdf=True)
    assert '<html lang="es">' in result.html
    assert ">Experiencia<" in result.html
    assert ">Experience<" not in result.html


def test_open_ended_role_ranks_as_ongoing_in_the_locales_own_words(es_project: Path) -> None:
    """wl-019 reads `ongoing.accepts`, so `Actualidad` outranks every real date.

    Reading only "Present" would rank the current role as undated, and the
    section would look correctly ordered whatever order it was in.
    """
    resolved = builder.resolve_project(es_project, "general", public=True)
    assert [f.rule_id for f in linter.lint(resolved, rule_ids=["wl-019"])] == []

    reversed_work = list(reversed(resolved.data["work"]))
    resolved.data["work"] = reversed_work
    assert [f.rule_id for f in linter.lint(resolved, rule_ids=["wl-019"])] == ["wl-019"]


def test_open_ended_date_exports_as_an_omitted_end_date(es_project: Path) -> None:
    """JSON Resume expresses a current role by omitting endDate, whatever the word."""
    doc = to_json_resume(builder.resolve_project(es_project, "general", public=True))
    current = next(w for w in doc["work"] if w["name"] == "Acme")
    assert "endDate" not in current
    assert doc["work"][1]["endDate"] == "2019-12"


def test_text_exports_head_sections_in_the_locales_words(es_project: Path) -> None:
    """A Spanish PDF with an English DOCX beside it is the failure this prevents."""
    md = to_markdown(builder.resolve_project(es_project, "general", public=True))
    assert "## Experiencia" in md
    assert "## Experience" not in md


def test_public_build_uses_the_packs_placeholder_contact(tmp_path: Path, packs_dir: Path) -> None:
    """--public must not fall back to an English stand-in identity."""
    (packs_dir / "es.yaml").write_text(_ES_PACK)
    files = {k: v for k, v in conftest._PROJECT_FILES.items() if not k.startswith("private/")}
    root = make_project(tmp_path, files=files, extra={"cvloom.yaml": "locale: es\n"})
    result = builder.build_project(root, profile_name="general", public=True, skip_pdf=True)
    assert "Su Nombre" in result.html
    assert "Your Name" not in result.html


def test_fallback_warnings_reach_resolved_profile(tmp_path: Path, packs_dir: Path) -> None:
    """A pack falling back to en must surface to the user, not stay silent.

    ResolvedProfile.warnings is the existing channel — the CLI already prints it.
    """
    (packs_dir / "xx.yaml").write_text(
        "html_lang: xx\n"
        "section_titles:\n  work: Trabajo\n"
        "ongoing:\n  render: Actualidad\n  accepts: [Actualidad]\n"
    )
    root = make_project(tmp_path, extra={"cvloom.yaml": "locale: xx\n"})
    resolved = builder.resolve_project(root, "general")
    assert any("placeholder_contact" in w for w in resolved.warnings)
