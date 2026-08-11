"""The deterministic context block: what it says, what it sheds, and in what order.

The bulk of this file is about *shedding*. A block that renders everything is easy
and wrong — it crowds the CV out of a small model's context window, and since the
grounding contract lives in the system message, an over-long prompt loses the
anti-fabrication rules before it loses anything else.
"""

from __future__ import annotations

import pytest

from cvloom.ai.analysis import (
    LEVEL_COMPACT,
    LEVEL_COUNTS,
    LEVEL_GROUPED,
    SCOPE_BRIEF,
    SCOPE_EVIDENCE,
    SCOPE_FULL,
    analysis_context_block,
)
from cvloom.linter import LintFinding
from cvloom.locale import load_pack
from tests.conftest import make_resolved

_CV = "Jane Doe | Senior Engineer\n\n" + ("Built and shipped things. " * 60)


def _resolved(**kwargs: object) -> object:
    return make_resolved(
        work=[
            {
                "company": "Acme Corp",
                "title": "Engineer",
                "start_date": "2020-01",
                "end_date": "Present",
                "highlights": ["Cut deploy time by 40% across twelve services."],
            },
            {
                "company": "Globex",
                "title": "Engineer",
                "start_date": "2018-01",
                "end_date": "2019-12",
                "highlights": ["Responsible for maintaining the billing system."],
            },
        ],
        skills=[{"category": "Languages", "items": ["Python"]}],
        show={"work": True, "skills": True},
        section_order=["work", "skills"],
        **kwargs,  # type: ignore[arg-type]
    )


def _block(scope: str = SCOPE_FULL, cv: str = _CV):  # type: ignore[no-untyped-def]
    return analysis_context_block(_resolved(), cv, scope=scope)


# ── What the block reports ──────────────────────────────────────────


def test_the_block_is_tagged_so_the_prompt_can_refer_to_it() -> None:
    text = _block().text
    assert text.startswith("<analysis>")
    assert text.endswith("</analysis>")


def test_the_block_reports_length_template_and_finding_counts() -> None:
    """The three things no amount of reading the CV text would reveal."""
    text = _block().text
    assert "length:" in text
    assert "template: cv/ats-clean" in text
    assert "findings:" in text


def test_an_unrated_template_is_reported_as_unknown_not_omitted() -> None:
    """`templates_meta` reports an unknown template as unknown rather than assuming
    it is safe, and the block must not quietly launder that into silence."""
    block = analysis_context_block(_resolved(template_name="custom/mine"), _CV)
    assert "parse risk unknown" in block.text


def test_rules_that_did_not_run_are_named() -> None:
    """On a locale with partial rule coverage, "no readability finding" must not be
    readable as "readable"."""
    block = analysis_context_block(_resolved(locale_pack=load_pack("es")[0]), _CV)
    assert "lint rules ran" in block.text
    assert "no es implementation" in block.text


def test_the_english_trim_recommendations_never_leak_into_a_spanish_block() -> None:
    """`TrimReport.recommendations` are hardcoded English sentences. The block emits
    the numbers and writes its own framing instead."""
    from cvloom import trim

    resolved = _resolved(locale_pack=load_pack("es")[0])
    block = analysis_context_block(resolved, _CV)
    for recommendation in trim.analyze(resolved).recommendations:  # type: ignore[arg-type]
        assert recommendation not in block.text


# ── Grouping and ordering ───────────────────────────────────────────


def _synthetic(count: int, rule_id: str, severity: str, category: str, hint: str = "fix it"):  # type: ignore[no-untyped-def]
    return [
        LintFinding(
            rule_id=rule_id,
            severity=severity,
            section="work",
            entry=f"Entry {i}",
            bullet_index=i,
            bullet_text="text",
            message=f"problem {i}",
            fix_hint=hint,
            category=category,
        )
        for i in range(count)
    ]


def test_the_fix_hint_is_stated_once_per_rule_not_once_per_finding(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A rule's hint is constant across its findings; repeating it spends most of
    the block's budget saying the same sentence."""
    from cvloom.ai import analysis

    hint = "Add a metric to at least one bullet."
    monkeypatch.setattr(
        analysis.linter, "lint", lambda r: _synthetic(3, "wl-002", "warning", "writing", hint)
    )
    assert _block().text.count(hint) == 1


def test_a_rule_with_two_distinct_hints_stays_two_groups(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Grouping is keyed on (rule_id, fix_hint): collapsing on rule_id alone would
    attach one group's advice to the other group's findings."""
    from cvloom.ai import analysis

    findings = _synthetic(1, "wl-016", "warning", "writing", "first hint") + _synthetic(
        1, "wl-016", "warning", "writing", "second hint"
    )
    monkeypatch.setattr(analysis.linter, "lint", lambda r: findings)
    text = _block().text
    assert "first hint" in text
    assert "second hint" in text


def test_parse_findings_outrank_writing_findings_at_equal_severity(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """An ats-parse finding means a machine may not read the line at all, which
    outranks any judgement about how well it is written."""
    from cvloom.ai import analysis

    findings = _synthetic(1, "wl-100", "warning", "writing") + _synthetic(
        1, "wl-200", "warning", "ats-parse"
    )
    monkeypatch.setattr(analysis.linter, "lint", lambda r: findings)
    text = _block().text
    assert text.index("wl-200") < text.index("wl-100")


def test_severity_outranks_category(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from cvloom.ai import analysis

    findings = _synthetic(1, "wl-100", "warning", "writing") + _synthetic(
        1, "wl-200", "info", "ats-parse"
    )
    monkeypatch.setattr(analysis.linter, "lint", lambda r: findings)
    text = _block().text
    assert text.index("wl-100") < text.index("wl-200")


def test_instances_are_capped_per_rule_and_the_remainder_is_counted(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from cvloom.ai import analysis

    monkeypatch.setattr(
        analysis.linter, "lint", lambda r: _synthetic(9, "wl-005", "warning", "writing")
    )
    text = _block().text
    assert "and 6 more of wl-005" in text


# ── The weak-opener constraint ──────────────────────────────────────


def _opener_block(highlight: str, code: str = "en", scope: str = SCOPE_FULL):  # type: ignore[no-untyped-def]
    resolved = make_resolved(
        work=[
            {
                "company": "Acme Corp",
                "title": "Engineer",
                "start_date": "2020-01",
                "end_date": "Present",
                "highlights": [highlight],
            }
        ],
        skills=[{"category": "Languages", "items": ["Python"]}],
        show={"work": True, "skills": True},
        section_order=["work", "skills"],
        locale_pack=load_pack(code)[0],
    )
    return analysis_context_block(resolved, _CV, scope=scope)


def test_a_weak_opener_finding_brings_the_whole_flagged_set_with_it() -> None:
    """Told only that one opener is weak, a model rewrites it into another one and
    the finding fires again on the bullet it just fixed."""
    text = _opener_block("Helped the team ship the new billing service on time.").text
    for opener in ("helped", "assisted", "was responsible for", "was involved in"):
        assert f'"{opener}"' in text
    assert "Any other verb is yours to choose." in text


def test_the_constraint_is_absent_without_a_weak_opener_finding() -> None:
    """Otherwise it is permanent prompt weight, paid for on every call."""
    text = _opener_block("Cut deploy time by 40% across twelve services.").text
    assert "yours to choose" not in text
    assert '"assisted"' not in text


def test_the_spanish_constraint_carries_the_spanish_openers() -> None:
    """The `es` set is cvloom's own editorial judgement — fourteen phrases no
    model can guess, which is what makes sending it worth the tokens."""
    text = _opener_block("Ayudé a migrar el monolito a una arquitectura de servicios.", "es").text
    assert '"ayudé a"' in text
    assert '"estuve involucrada en"' in text
    assert '"helped"' not in text, "the openers follow the CV's language"


def test_the_constraint_never_suggests_verbs_to_use_instead() -> None:
    """Five verbs presented as a menu is what collapses generated bullets onto the
    same vocabulary — the reason wl-004's own fix hint stopped naming them."""
    text = _opener_block("Helped the team ship the new billing service on time.").text
    for verb in ("Designed", "Implemented", "Reduced", "Delivered", "Architected"):
        assert verb not in text


def test_the_narrow_scopes_never_carry_the_constraint() -> None:
    """`cover` gets no defect findings at all, and `align` cannot act on the
    wording of one bullet."""
    for scope in (SCOPE_BRIEF, SCOPE_EVIDENCE):
        text = _opener_block("Helped the team ship the new billing service.", scope=scope).text
        assert "yours to choose" not in text, scope


# ── The budget and the downward walk ────────────────────────────────


def test_the_block_is_byte_stable_across_calls() -> None:
    """`complete_json` passes a seed where the backend accepts one, which buys
    nothing if the prompt differs run to run."""
    assert _block().text == _block().text


def test_a_flood_of_findings_degrades_rather_than_crowding_out_the_cv(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from cvloom.ai import analysis

    findings = [
        f
        for i in range(40)
        for f in _synthetic(5, f"wl-{i:03d}", "warning", "writing", f"hint number {i}")
    ]
    monkeypatch.setattr(analysis.linter, "lint", lambda r: findings)
    block = _block()
    assert block.level in (LEVEL_COMPACT, LEVEL_COUNTS)
    assert block.findings_total == 200
    assert block.notes, "degradation must be reported, not absorbed silently"


def test_shed_findings_are_named_rather_than_vanishing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A group dropped for budget still gets a line, so nothing is invisible."""
    from cvloom.ai import analysis

    findings = [
        f
        for i in range(12)
        for f in _synthetic(2, f"wl-{i:03d}", "warning", "writing", f"hint number {i}")
    ]
    monkeypatch.setattr(analysis.linter, "lint", lambda r: findings)
    block = _block()
    if block.level == LEVEL_GROUPED:
        assert "not shown:" in block.text


def test_a_healthy_run_reports_nothing_to_the_user() -> None:
    """A notice that is always on is a notice nobody reads.

    A CV long enough to earn a proportional budget renders every group at full
    detail, so nothing is shed and the user sees no notice at all.
    """
    block = _block(cv="Jane Doe | Engineer\n\n" + "word " * 1200)
    assert block.level == LEVEL_GROUPED
    assert block.notes == ()


def test_the_counts_floor_always_reports_itself(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Counts alone leave the model nothing to act on, so reaching that level is an
    event rather than a graceful landing."""
    from cvloom.ai import analysis

    findings = [
        f
        for i in range(80)
        for f in _synthetic(5, f"wl-{i:03d}", "warning", "writing", f"hint number {i}")
    ]
    monkeypatch.setattr(analysis.linter, "lint", lambda r: findings)
    block = _block(cv="short cv")
    assert block.level == LEVEL_COUNTS
    assert block.notes


# ── Scope ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("scope", [SCOPE_BRIEF, SCOPE_EVIDENCE])
def test_the_narrow_scopes_carry_no_per_bullet_detail(scope: str) -> None:
    """Neither a cover letter nor a JD alignment can act on the wording of one
    bullet, and handing a temperature-0.7 prompt a "no metric here" finding is an
    invitation to invent the metric."""
    text = _block(scope=scope).text
    assert "— fix:" not in text
    assert "bullet " not in text


def test_the_evidence_scope_names_what_to_lead_with_not_what_is_missing() -> None:
    """Derived from the *absence* of the quantification rule, so it reads as
    evidence rather than as a gap to fill."""
    text = _block(scope=SCOPE_EVIDENCE).text
    assert "entries with a quantified outcome: work/Acme Corp" in text
    assert "Globex" not in text


def test_the_evidence_scope_withholds_the_writing_tone_summary() -> None:
    """`align` gets it because a mismatched register is a real tone gap; `cover`
    gets no defect signal at all."""
    assert "most frequent writing findings" in _block(scope=SCOPE_BRIEF).text
    assert "most frequent writing findings" not in _block(scope=SCOPE_EVIDENCE).text
