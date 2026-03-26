"""Tests for the ATS linter."""

from __future__ import annotations

from cvloom.linter import lint
from cvloom.models import ResolvedProfile


def _make_resolved(
    work: list | None = None,
    education: list | None = None,
    projects: list | None = None,
    skills: list | None = None,
) -> ResolvedProfile:
    """Create a minimal ResolvedProfile for linter testing."""
    return ResolvedProfile(
        profile={},
        data={
            "basics": {"headline": "Engineer", "summary": "A summary."},
            "work": work or [],
            "education": education or [],
            "skills": skills or [],
            "projects": projects or [],
            "contact": {"name": "Test", "email": "t@t.com"},
        },
        show_sections={"work": True, "education": True, "skills": True, "projects": True},
        section_order=["skills", "work", "education", "projects"],
        template_name="cv/ats-single",
        output_filename="cv",
    )


# ── ats-001: passive voice ──────────────────────────────────────────


def test_passive_voice_detected():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["The system was designed to handle load."]},
    ])
    findings = lint(resolved, rule_ids=["ats-001"])
    assert len(findings) == 1
    assert findings[0].rule_id == "ats-001"
    assert "Passive voice" in findings[0].message


def test_passive_voice_clean():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Designed a system to handle 10k req/s."]},
    ])
    findings = lint(resolved, rule_ids=["ats-001"])
    assert len(findings) == 0


# ── ats-002: missing quantification ─────────────────────────────────


def test_missing_quantification_detected():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Improved system performance significantly."]},
    ])
    findings = lint(resolved, rule_ids=["ats-002"])
    assert len(findings) == 1
    assert findings[0].rule_id == "ats-002"


def test_quantification_present():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Reduced latency by 40%."]},
    ])
    findings = lint(resolved, rule_ids=["ats-002"])
    assert len(findings) == 0


# ── ats-003: noise skills ───────────────────────────────────────────


def test_noise_skill_detected():
    resolved = _make_resolved(skills=[
        {"category": "Office", "items": ["Microsoft Word", "Python"]},
    ])
    findings = lint(resolved, rule_ids=["ats-003"])
    assert len(findings) == 1
    assert findings[0].rule_id == "ats-003"
    assert "Microsoft Word" in findings[0].message


def test_noise_skill_clean():
    resolved = _make_resolved(skills=[
        {"category": "Languages", "items": ["Python", "Go"]},
    ])
    findings = lint(resolved, rule_ids=["ats-003"])
    assert len(findings) == 0


def test_noise_skill_with_level_objects():
    resolved = _make_resolved(skills=[
        {"category": "Office", "items": [{"name": "Microsoft Excel", "level": "expert"}]},
    ])
    findings = lint(resolved, rule_ids=["ats-003"])
    assert len(findings) == 1


# ── ats-004: weak action verbs ──────────────────────────────────────


def test_weak_verb_detected():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Helped build the deployment pipeline."]},
    ])
    findings = lint(resolved, rule_ids=["ats-004"])
    assert len(findings) == 1
    assert "helped" in findings[0].message.lower()


def test_strong_verb_clean():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Architected the deployment pipeline."]},
    ])
    findings = lint(resolved, rule_ids=["ats-004"])
    assert len(findings) == 0


# ── ats-005: highlight length ───────────────────────────────────────


def test_highlight_too_short():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Built things."]},
    ])
    findings = lint(resolved, rule_ids=["ats-005"])
    assert len(findings) == 1
    assert "too short" in findings[0].message.lower()


def test_highlight_too_long():
    long_text = " ".join(["word"] * 30)
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": [long_text]},
    ])
    findings = lint(resolved, rule_ids=["ats-005"])
    assert len(findings) == 1
    assert "too long" in findings[0].message.lower()


def test_highlight_good_length():
    text = "Built a scalable pipeline processing 50k events per second with Kafka."
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": [text]},
    ])
    findings = lint(resolved, rule_ids=["ats-005"])
    assert len(findings) == 0


# ── Aggregation ─────────────────────────────────────────────────────


def test_lint_all_rules():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": [
                "Helped with stuff.",  # ats-004 + ats-005
                "The system was built.",  # ats-001 + ats-002 + ats-005
            ]},
        ],
        skills=[
            {"category": "Office", "items": ["Microsoft Word"]},  # ats-003
        ],
    )
    findings = lint(resolved)
    rule_ids = {f.rule_id for f in findings}
    assert "ats-001" in rule_ids
    assert "ats-002" in rule_ids
    assert "ats-003" in rule_ids
    assert "ats-004" in rule_ids
    assert "ats-005" in rule_ids


def test_lint_hidden_section_skipped():
    resolved = _make_resolved(
        work=[{"company": "Acme", "highlights": ["Helped."]}],
    )
    resolved.show_sections["work"] = False
    findings = lint(resolved)
    work_findings = [f for f in findings if f.section == "work"]
    assert len(work_findings) == 0


def test_lint_rule_filter():
    resolved = _make_resolved(
        work=[{"company": "Acme", "highlights": ["Helped."]}],
        skills=[{"category": "Office", "items": ["Microsoft Word"]}],
    )
    findings = lint(resolved, rule_ids=["ats-003"])
    assert all(f.rule_id == "ats-003" for f in findings)
