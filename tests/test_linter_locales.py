"""Tests for per-locale linter data and locale-aware rule dispatch.

The Spanish rules are tested through their observable findings rather than
through their lexicons: a test asserting that "proactivo" is in a set restates
the source file, while a test asserting that a well-written Spanish bullet
produces no wl-007 finding is the property the feature actually promises.
"""

from __future__ import annotations

from typing import Any

import pytest

from cvloom import linter, locale
from cvloom.linter_locales import LintLocale, available_locales, pack_for
from cvloom.models import ResolvedProfile
from tests.conftest import make_resolved

# ---------------------------------------------------------------------------
# Selecting a pack
# ---------------------------------------------------------------------------


def test_available_locales_lists_the_shipped_packs() -> None:
    assert available_locales() == ("en", "es")


@pytest.mark.parametrize("code", ["en", "es"])
def test_pack_for_returns_the_matching_pack(code: str) -> None:
    assert pack_for(code).code == code


def test_pack_for_unknown_locale_falls_back_to_english() -> None:
    """A document pack can exist with no linter data behind it.

    Someone contributing cvloom/locales/fr.yaml gets a French document before
    anyone writes French lexicons. That CV is graded with English heuristics —
    imperfect, and reported as such by rules_for — rather than crashing.
    """
    assert pack_for("fr").code == "en"


def test_every_shipped_document_pack_resolves_to_linter_data() -> None:
    """Not a tautology: it fails the day a locale ships without linter data."""
    for code in locale.available_locales():
        assert pack_for(code).code == code


def test_lint_locale_is_frozen() -> None:
    """The packs are module-level singletons shared process-wide."""
    with pytest.raises(Exception):
        pack_for("en").min_skills = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Rule dispatch
# ---------------------------------------------------------------------------


def _ids(rules: list[linter.LintRule]) -> list[str]:
    return [r.rule_id for r in rules]


@pytest.mark.parametrize("code", ["en", "es"])
def test_every_rule_id_is_either_active_or_skipped(code: str) -> None:
    """No rule may fall out of the registry unaccounted for.

    Registering a rule for one locale and forgetting the other should surface as
    a skip the user is told about, never as a rule that silently vanished.
    """
    active, skipped = linter.rules_for(code)
    accounted = _ids(active) + _ids(skipped)
    assert sorted(accounted) == sorted({r.rule_id for r in linter.RULES})
    assert len(accounted) == len(set(accounted)), "a rule_id resolved twice"


def test_english_skips_the_spanish_only_rule() -> None:
    active, skipped = linter.rules_for("en")
    assert _ids(skipped) == ["wl-025"]
    assert "wl-016" in _ids(active)


def test_spanish_skips_only_readability() -> None:
    """Flesch-Kincaid's 6–12 band has no meaning on a Spanish ease scale."""
    active, skipped = linter.rules_for("es")
    assert _ids(skipped) == ["wl-016"]
    assert "wl-025" in _ids(active)


def test_a_locale_specific_implementation_wins_over_the_neutral_one() -> None:
    """wl-013 has an implementation per locale and must resolve to one each."""
    en_rule = next(r for r in linter.rules_for("en")[0] if r.rule_id == "wl-013")
    es_rule = next(r for r in linter.rules_for("es")[0] if r.rule_id == "wl-013")
    assert en_rule.check is not es_rule.check
    assert en_rule.name == "tense-consistency"
    assert es_rule.name == "style-consistency"


def test_unknown_locale_runs_the_language_neutral_rules() -> None:
    """A locale with no rules of its own still gets everything that is neutral."""
    active, skipped = linter.rules_for("fr")
    assert "wl-019" in _ids(active)  # chronological order — no language in it
    assert set(_ids(skipped)) == {"wl-007", "wl-013", "wl-016", "wl-025"}


# ---------------------------------------------------------------------------
# The Spanish rules
# ---------------------------------------------------------------------------


def _es(bullets: list[str], **kw: Any) -> ResolvedProfile:
    """A one-role Spanish profile, on the shipped es pack."""
    resolved = make_resolved(
        work=[
            {
                "company": "Acme",
                "title": "Ingeniera",
                "start_date": "2020-01",
                "end_date": "Actualidad",
                "highlights": bullets,
            }
        ],
        **kw,
    )
    resolved.locale, _ = locale.load_pack("es")
    return resolved


def _rule(bullets: list[str], rule_id: str, **kw: Any) -> list[linter.LintFinding]:
    return linter.lint(_es(bullets, **kw), rule_ids=[rule_id])


# ── wl-007: first person under pro-drop ─────────────────────────────


@pytest.mark.parametrize(
    "bullet",
    [
        "Lideré la migración del monolito y reduje el despliegue un 60%.",
        "Me encargué de la plataforma de pagos durante dos años.",
        "Diseñé la arquitectura de datos junto al equipo de producto.",
    ],
)
def test_conjugated_spanish_is_not_first_person(bullet: str) -> None:
    """The acceptance criterion for the whole feature.

    Spanish is pro-drop, so the subject lives in the conjugation and these are
    correct CV style. Porting English's pronoun list — `me` above all — would
    flag every well-formed bullet in the document and discredit every other
    finding printed beside it.
    """
    assert _rule([bullet], "wl-007") == []


@pytest.mark.parametrize(
    "bullet",
    [
        "Yo diseñé la arquitectura del sistema de pagos.",
        "Diseñé mi propio sistema de despliegue continuo.",
        "Presenté mis resultados en la conferencia interna.",
    ],
)
def test_explicit_spanish_pronouns_are_flagged(bullet: str) -> None:
    findings = _rule([bullet], "wl-007")
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-007"


# ── wl-001: pasiva refleja ──────────────────────────────────────────


def test_pasiva_refleja_is_flagged() -> None:
    """More common than the periphrastic form, and with no English shape."""
    findings = _rule(["Se implementó una plataforma de eventos con Kafka."], "wl-001")
    assert len(findings) == 1
    assert "Se implementó" in findings[0].message


def test_periphrastic_passive_is_flagged() -> None:
    findings = _rule(["El sistema fue migrado a microservicios en seis meses."], "wl-001")
    assert len(findings) == 1
    assert "fue migrado" in findings[0].message


@pytest.mark.parametrize(
    "bullet",
    [
        "Lideré la migración del monolito a microservicios.",
        "Se convirtió en el equipo de referencia de la empresa.",
    ],
)
def test_active_and_pronominal_spanish_is_clean(bullet: str) -> None:
    """`se convirtió` is pronominal, not passive — the `se` belongs to the verb."""
    assert _rule([bullet], "wl-001") == []


def test_the_fix_hint_names_spanish_verbs() -> None:
    """Suggesting 'Designed' to someone writing in Spanish is useless advice."""
    findings = _rule(["Se implementó una plataforma de eventos."], "wl-001")
    assert "Lideré" in findings[0].fix_hint
    assert "Designed" not in findings[0].fix_hint


# ── wl-013: style consistency ───────────────────────────────────────


def test_mixing_infinitive_and_preterite_is_flagged() -> None:
    findings = _rule(
        [
            "Diseñar y mantener la plataforma de datos del equipo.",
            "Reduje la latencia p99 de 800 ms a 120 ms.",
        ],
        "wl-013",
    )
    assert len(findings) == 1
    assert "infinitive" in findings[0].message
    assert "first-person preterite" in findings[0].message


@pytest.mark.parametrize(
    "bullets",
    [
        ["Diseñé la plataforma de datos.", "Reduje la latencia un 40%."],
        ["Diseñar la plataforma de datos.", "Reducir la latencia un 40%."],
    ],
)
def test_one_style_throughout_is_clean(bullets: list[str]) -> None:
    """Both styles are conventional in Spanish; only mixing them is the flaw."""
    assert _rule(bullets, "wl-013") == []


def test_a_noun_ending_in_er_is_not_read_as_an_infinitive() -> None:
    """`Líder` ends like an infinitive but carries an accent, which one never does."""
    findings = _rule(
        ["Líder técnico de la plataforma de datos.", "Reduje la latencia un 40%."],
        "wl-013",
    )
    assert findings == []


def test_style_consistency_is_reported_per_role() -> None:
    """Two roles each consistent in their own style is not an inconsistency."""
    resolved = make_resolved(
        work=[
            {
                "company": "Acme",
                "title": "Ingeniera",
                "start_date": "2021-01",
                "end_date": "Actualidad",
                "highlights": ["Diseñar la plataforma.", "Mantener el pipeline."],
            },
            {
                "company": "Globex",
                "title": "Ingeniera",
                "start_date": "2018-01",
                "end_date": "2020-12",
                "highlights": ["Diseñé la API.", "Reduje la latencia un 40%."],
            },
        ]
    )
    resolved.locale, _ = locale.load_pack("es")
    assert linter.lint(resolved, rule_ids=["wl-013"]) == []


# ── wl-025: missing diacritics ──────────────────────────────────────


def test_missing_diacritic_is_flagged_with_the_correction() -> None:
    findings = _rule(["Lideré la migracion del sistema de pagos."], "wl-025")
    assert len(findings) == 1
    assert 'should be "migración"' in findings[0].message


def test_the_correction_keeps_the_original_capitalisation() -> None:
    findings = _rule(["Gestion del equipo de plataforma y de sus entregas."], "wl-025")
    assert 'should be "Gestión"' in findings[0].message


def test_correctly_accented_spanish_is_clean() -> None:
    assert _rule(["Lideré la migración del sistema de gestión de pagos."], "wl-025") == []


def test_diacritics_are_checked_in_the_summary_too() -> None:
    resolved = _es(["Lideré la migración."], basics={"summary": "Ingeniera con formacion técnica."})
    findings = linter.lint(resolved, rule_ids=["wl-025"])
    assert [f.section for f in findings] == ["basics"]


def test_the_diacritic_rule_does_not_run_in_english() -> None:
    """`version` and `area` are ordinary English words; flagging them is nonsense."""
    resolved = make_resolved(
        work=[
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2020-01",
                "highlights": ["Shipped version 2 of the reporting area dashboard."],
            }
        ]
    )
    assert linter.lint(resolved, rule_ids=["wl-025"]) == []


# ── Ported lexicons and thresholds ──────────────────────────────────


def test_spanish_weak_openers_are_flagged() -> None:
    findings = _rule(["Ayudé a migrar el monolito a microservicios."], "wl-004")
    assert len(findings) == 1
    assert "ayudé a" in findings[0].message


def test_spanish_collaboration_openers_are_not_flagged() -> None:
    """`colaboré en` and `contribuí a` came out with English `contributed to`."""
    assert _rule(["Colaboré en el rediseño de la plataforma."], "wl-004") == []
    assert _rule(["Contribuí a la migración del monolito."], "wl-004") == []


def test_spanish_gendered_openers_are_carried_as_complete_pairs() -> None:
    """Only the adjectival openers inflect; missing one half would flag one
    gender's phrasing and not the other's."""
    pairs = ("Encargado de", "Encargada de", "Estuve involucrado en", "Estuve involucrada en")
    for opener in pairs:
        assert len(_rule([f"{opener} la migración del monolito."], "wl-004")) == 1, opener


def test_a_strong_opener_sharing_a_prefix_is_not_flagged() -> None:
    """`Formé a tres ingenieros` is strong; only `formé parte de` is weak."""
    assert _rule(["Formé a tres ingenieros junior del equipo."], "wl-004") == []


def test_highlight_length_uses_the_scaled_spanish_bounds() -> None:
    """A nine-word bullet is long enough in English and short in Spanish.

    10/30 rather than 8/25, scaled by the ratio measured from matched en/es
    renders of the same CV.
    """
    nine_words = "Diseñé la plataforma de datos del equipo de producto."
    assert len(nine_words.split()) == 9
    findings = _rule([nine_words], "wl-005")
    assert len(findings) == 1
    assert "min 10" in findings[0].message


def test_spanish_metrics_are_recognised() -> None:
    """A euro amount and a dot-grouped thousand are metrics; English missed both."""
    lex: LintLocale = pack_for("es")
    assert lex.metric_pattern.search("Ahorré 40.000 € anuales en infraestructura.")
    assert lex.metric_pattern.search("Procesé 50 millones de eventos al día.")
