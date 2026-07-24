"""Tests for the writing lint."""

from __future__ import annotations

from cvloom.linter import (
    CATEGORY_ATS_PARSE,
    CATEGORY_STRUCTURE,
    CATEGORY_WRITING,
    RULES,
    category_counts,
    lint,
)
from cvloom.models import ResolvedProfile
from tests.conftest import make_resolved


def _make_resolved(
    work: list | None = None,
    education: list | None = None,
    projects: list | None = None,
    skills: list | None = None,
    basics: dict | None = None,
    contact: dict | None = None,
    template_name: str = "cv/ats-single",
) -> ResolvedProfile:
    """Create a minimal ResolvedProfile for linter testing."""
    return make_resolved(
        work=work,
        education=education,
        projects=projects,
        skills=skills,
        basics=basics,
        contact=contact,
        template_name=template_name,
    )


# ── wl-001: passive voice ──────────────────────────────────────────


def test_passive_voice_detected():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["The system was designed to handle load."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-001"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-001"
    assert "Passive voice" in findings[0].message


def test_passive_voice_clean():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["Designed a system to handle 10k req/s."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-001"])
    assert len(findings) == 0


def test_passive_voice_false_positive_adjective():
    """Adjectives like 'present', 'efficient', 'built' should not flag."""
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": [
                    "The system is present in every data center across the region.",
                    "The architecture was efficient and reduced overall compute costs.",
                    "The pipeline was built to process events at scale with Kafka.",
                ],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-001"])
    # Only "was built" should NOT flag (built is in false positives).
    # "is present" and "was efficient" should NOT flag (adjectives).
    assert len(findings) == 0


# ── wl-002: missing quantification ─────────────────────────────────


def test_missing_quantification_detected():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["Improved system performance significantly."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-002"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-002"


def test_quantification_present():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["Reduced latency by 40%."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-002"])
    assert len(findings) == 0


# ── wl-003: noise skills ───────────────────────────────────────────


def test_noise_skill_detected():
    resolved = _make_resolved(
        skills=[
            {"category": "Office", "items": ["Microsoft Word", "Python"]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-003"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-003"
    assert "Microsoft Word" in findings[0].message


def test_noise_skill_clean():
    resolved = _make_resolved(
        skills=[
            {"category": "Languages", "items": ["Python", "Go"]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-003"])
    assert len(findings) == 0


def test_noise_skill_with_level_objects():
    resolved = _make_resolved(
        skills=[
            {"category": "Office", "items": [{"name": "Microsoft Excel", "level": "expert"}]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-003"])
    assert len(findings) == 1


# ── wl-004: weak action verbs ──────────────────────────────────────


def test_weak_verb_detected():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["Helped build the deployment pipeline."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-004"])
    assert len(findings) == 1
    assert "helped" in findings[0].message.lower()


def test_strong_verb_clean():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["Architected the deployment pipeline."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-004"])
    assert len(findings) == 0


# ── wl-005: highlight length ───────────────────────────────────────


def test_highlight_too_short():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["Built things."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-005"])
    assert len(findings) == 1
    assert "too short" in findings[0].message.lower()


def test_highlight_too_long():
    long_text = " ".join(["word"] * 30)
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": [long_text]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-005"])
    assert len(findings) == 1
    assert "too long" in findings[0].message.lower()


def test_highlight_good_length():
    text = "Built a scalable pipeline processing 50k events per second with Kafka."
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": [text]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-005"])
    assert len(findings) == 0


# ── Aggregation ─────────────────────────────────────────────────────


def test_lint_all_rules():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": [
                    "Helped with stuff.",  # wl-004 + wl-005
                    "The system was designed.",  # wl-001 + wl-002 + wl-005
                ],
            },  # 2 highlights → wl-006
        ],
        skills=[
            {"category": "Office", "items": ["Microsoft Word"]},  # wl-003 + wl-009 (1 < 8)
        ],
        basics={"headline": "Engineer", "summary": "I am a motivated engineer."},  # wl-007+wl-008
        # no linkedin/github in contact → wl-010
    )
    findings = lint(resolved)
    rule_ids = {f.rule_id for f in findings}
    assert "wl-001" in rule_ids
    assert "wl-002" in rule_ids
    assert "wl-003" in rule_ids
    assert "wl-004" in rule_ids
    assert "wl-005" in rule_ids
    assert "wl-006" in rule_ids
    assert "wl-007" in rule_ids
    assert "wl-008" in rule_ids
    assert "wl-009" in rule_ids
    assert "wl-010" in rule_ids


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
    findings = lint(resolved, rule_ids=["wl-003"])
    assert all(f.rule_id == "wl-003" for f in findings)


# ── wl-006: bullet count ───────────────────────────────────────────


def test_bullet_count_too_few():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": ["Built a high-availability system with 99.9% uptime."],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-006"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-006"
    assert "minimum" in findings[0].message


def test_bullet_count_too_many():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": [f"Delivered feature {i} on schedule." for i in range(9)],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-006"])
    assert len(findings) == 1
    assert "maximum" in findings[0].message


def test_bullet_count_ok():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": [
                    "Built a pipeline processing 1M events per day.",
                    "Reduced deployment time by 40% via automation.",
                    "Mentored 3 junior engineers to promotion.",
                    "Shipped 5 features ahead of schedule.",
                ],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-006"])
    assert len(findings) == 0


# ── wl-007: first-person pronouns ─────────────────────────────────


def test_first_person_in_highlight():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": ["I led the team to deliver the product 2 weeks early."],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-007"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-007"


def test_first_person_in_summary():
    resolved = _make_resolved(
        basics={"headline": "Engineer", "summary": "My approach focuses on delivering value."},
    )
    findings = lint(resolved, rule_ids=["wl-007"])
    assert len(findings) == 1
    assert findings[0].section == "basics"


def test_first_person_clean():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": ["Led the team to deliver the product 2 weeks early."],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-007"])
    assert len(findings) == 0


# ── wl-008: vague buzzwords ────────────────────────────────────────


def test_vague_buzzword_in_highlight():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": [
                    "A proactive engineer who delivered 3 features per sprint.",
                ],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-008"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-008"
    assert "proactive" in findings[0].message


def test_vague_buzzword_in_summary():
    resolved = _make_resolved(
        basics={"headline": "Engineer", "summary": "Passionate engineer with 5 years experience."},
    )
    findings = lint(resolved, rule_ids=["wl-008"])
    assert len(findings) == 1
    assert findings[0].section == "basics"


def test_vague_buzzword_clean():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": [
                    "Reduced infrastructure costs by 30% using spot instances.",
                ],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-008"])
    assert len(findings) == 0


# ── wl-009: skill count ────────────────────────────────────────────


def test_skill_count_too_few():
    resolved = _make_resolved(
        skills=[
            {"category": "Languages", "items": ["Python", "Go", "Rust"]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-009"])
    assert len(findings) == 1
    assert "minimum" in findings[0].message


def test_skill_count_too_many():
    resolved = _make_resolved(
        skills=[
            {"category": "Languages", "items": [f"Skill{i}" for i in range(30)]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-009"])
    assert len(findings) == 1
    assert "maximum" in findings[0].message


def test_skill_count_ok():
    resolved = _make_resolved(
        skills=[
            {"category": "Languages", "items": ["Python", "Go", "Rust", "TypeScript"]},
            {"category": "Tools", "items": ["Docker", "Kubernetes", "Terraform", "Git", "Kafka"]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-009"])
    assert len(findings) == 0


# ── wl-010: profile links ──────────────────────────────────────────


def test_no_profile_links():
    resolved = _make_resolved(
        contact={"name": "Test", "email": "t@example.com"},
    )
    findings = lint(resolved, rule_ids=["wl-010"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-010"


def test_profile_link_in_contact():
    resolved = _make_resolved(
        contact={"name": "Test", "email": "t@example.com", "linkedin": "https://linkedin.com/in/test"},
    )
    findings = lint(resolved, rule_ids=["wl-010"])
    assert len(findings) == 0


def test_profile_link_in_public_links():
    resolved = _make_resolved(
        basics={
            "headline": "Engineer",
            "summary": "A summary.",
            "public_links": [{"label": "GitHub", "url": "https://github.com/test"}],
        },
    )
    findings = lint(resolved, rule_ids=["wl-010"])
    assert len(findings) == 0


# ── wl-011: page count ─────────────────────────────────────────────


def test_page_count_exceeded():
    long_highlight = " ".join(["achievement"] * 50)  # 50 words each
    resolved = _make_resolved(
        work=[
            {"company": f"Company{i}", "highlights": [long_highlight] * 5}
            for i in range(6)  # 6 * 5 * 50 = 1500 words
        ]
    )
    findings = lint(resolved, rule_ids=["wl-011"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-011"
    assert "pages" in findings[0].message


def test_page_count_ok():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": [
                    "Built a scalable pipeline processing 1M events per day.",
                    "Reduced deployment time by 40% via CI/CD automation.",
                    "Mentored 3 junior engineers to staff-level promotions.",
                ],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-011"])
    assert len(findings) == 0


def test_page_count_academic_skipped():
    long_highlight = " ".join(["achievement"] * 50)
    resolved = _make_resolved(
        work=[{"company": f"Company{i}", "highlights": [long_highlight] * 5} for i in range(6)],
        template_name="cv/academic",
    )
    findings = lint(resolved, rule_ids=["wl-011"])
    assert len(findings) == 0


# ── wl-012: date format consistency ────────────────────────────────


def test_date_format_mixed_within_section():
    resolved = _make_resolved(
        work=[
            {"company": "A", "start_date": "2020-01", "end_date": "Present", "highlights": []},
            {"company": "B", "start_date": "2018", "end_date": "2020", "highlights": []},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-012"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-012"
    assert "YYYY-MM" in findings[0].message
    assert "YYYY" in findings[0].message


def test_date_format_consistent():
    resolved = _make_resolved(
        work=[
            {"company": "A", "start_date": "2020-01", "end_date": "Present", "highlights": []},
            {"company": "B", "start_date": "2018-03", "end_date": "2020-01", "highlights": []},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-012"])
    assert len(findings) == 0


def test_date_format_sections_independent():
    # Work uses YYYY-MM, education uses YYYY — each section is internally consistent.
    resolved = _make_resolved(
        work=[
            {"company": "A", "start_date": "2020-01", "end_date": "Present", "highlights": []},
        ],
        education=[
            {"institution": "U", "start_date": "2016", "end_date": "2020", "highlights": []},
        ],
    )
    findings = lint(resolved, rule_ids=["wl-012"])
    assert len(findings) == 0


# ── wl-013: tense consistency ──────────────────────────────────────


def test_tense_past_in_current_role():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "end_date": "Present",
                "highlights": ["Led the platform team to deliver 3 services ahead of schedule."],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-013"])
    assert len(findings) == 1
    assert "past-tense" in findings[0].message.lower()


def test_tense_present_in_past_role():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "end_date": "2022-01",
                "highlights": ["Design a microservices platform handling 50k requests per second."],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-013"])
    assert len(findings) == 1
    assert "present-tense" in findings[0].message.lower()


def test_tense_correct_past_role():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "end_date": "2022-01",
                "highlights": ["Led the platform team to deliver 3 services ahead of schedule."],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-013"])
    assert len(findings) == 0


def test_tense_correct_current_role():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "end_date": "Present",
                "highlights": ["Lead the platform team delivering 3 services ahead of schedule."],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-013"])
    assert len(findings) == 0


# ── wl-014: summary length ─────────────────────────────────────────


def test_summary_too_short():
    resolved = _make_resolved(
        basics={"headline": "Engineer", "summary": "Backend engineer."},
    )
    findings = lint(resolved, rule_ids=["wl-014"])
    assert len(findings) == 1
    assert "too short" in findings[0].message.lower()


def test_summary_too_long():
    long_summary = " ".join(["word"] * 90)
    resolved = _make_resolved(
        basics={"headline": "Engineer", "summary": long_summary},
    )
    findings = lint(resolved, rule_ids=["wl-014"])
    assert len(findings) == 1
    assert "too long" in findings[0].message.lower()


def test_summary_good_length():
    summary = (
        "Experienced backend engineer with 5 years building scalable distributed systems "
        "in Python and Go, delivering measurable reliability improvements across production."
    )
    resolved = _make_resolved(
        basics={"headline": "Engineer", "summary": summary},
    )
    findings = lint(resolved, rule_ids=["wl-014"])
    assert len(findings) == 0


# ── wl-015: action→result pattern ─────────────────────────────────


def test_action_result_metric_without_framing():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["Reduced latency by 40%."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-015"])
    assert len(findings) == 1
    assert findings[0].rule_id == "wl-015"
    assert findings[0].severity == "suggestion"


def test_action_result_metric_with_framing():
    resolved = _make_resolved(
        work=[
            {
                "company": "Acme",
                "highlights": ["Reduced latency by 40%, enabling 3x more traffic through the API."],
            },
        ]
    )
    findings = lint(resolved, rule_ids=["wl-015"])
    assert len(findings) == 0


def test_action_result_no_metric_no_finding():
    resolved = _make_resolved(
        work=[
            {"company": "Acme", "highlights": ["Led the platform team to ship 5 features."]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-015"])
    assert len(findings) == 0


# ── wl-016: readability ─────────────────────────────────────────────


def test_readability_high_grade_flagged() -> None:
    hl = (
        "Architected microservices infrastructure incorporating"
        " containerization orchestration technologies."
    )
    resolved = _make_resolved(work=[{"company": "Acme", "highlights": [hl]}])
    findings = lint(resolved, rule_ids=["wl-016"])
    assert any(f.rule_id == "wl-016" and "exceeds" in f.message for f in findings)


def test_readability_low_grade_flagged() -> None:
    resolved = _make_resolved(work=[{"company": "Acme", "highlights": ["Did work."]}])
    findings = lint(resolved, rule_ids=["wl-016"])
    assert any(f.rule_id == "wl-016" and "below" in f.message for f in findings)


def test_readability_acceptable_no_finding() -> None:
    hl = "Led backend team to deliver Python REST API serving 5k users daily."
    resolved = _make_resolved(work=[{"company": "Acme", "highlights": [hl]}])
    findings = lint(resolved, rule_ids=["wl-016"])
    assert not findings


def test_readability_projects_checked() -> None:
    hl = (
        "Architected microservices infrastructure incorporating"
        " containerization orchestration technologies."
    )
    resolved = _make_resolved(
        projects=[
            {"name": "P", "description": "", "tags": [], "highlights": [hl]},
        ]
    )
    findings = lint(resolved, rule_ids=["wl-016"])
    assert any(f.rule_id == "wl-016" for f in findings)


# ── wl-017: tech-mentions-in-work ───────────────────────────────────


def test_tech_mentions_missing_flagged() -> None:
    resolved = _make_resolved(
        work=[{"company": "Acme", "highlights": ["Led a team and delivered projects on time."]}],
        skills=[{"category": "Languages", "items": ["Python", "Go"]}],
    )
    findings = lint(resolved, rule_ids=["wl-017"])
    assert any(f.rule_id == "wl-017" for f in findings)


def test_tech_mentions_present_no_finding() -> None:
    resolved = _make_resolved(
        work=[{"company": "Acme", "highlights": ["Built services in Python, cutting latency."]}],
        skills=[{"category": "Languages", "items": ["Python", "Go"]}],
    )
    findings = lint(resolved, rule_ids=["wl-017"])
    assert not findings


def test_tech_mentions_no_skills_skipped() -> None:
    resolved = _make_resolved(
        work=[{"company": "Acme", "highlights": ["Led a team."]}],
        skills=[],
    )
    findings = lint(resolved, rule_ids=["wl-017"])
    assert not findings


def test_tech_mentions_empty_highlights_skipped() -> None:
    resolved = _make_resolved(
        work=[{"company": "Acme", "highlights": []}],
        skills=[{"category": "Languages", "items": ["Python"]}],
    )
    findings = lint(resolved, rule_ids=["wl-017"])
    assert not findings


# ── categories ──────────────────────────────────────────────────────

_VALID_CATEGORIES = {CATEGORY_WRITING, CATEGORY_STRUCTURE, CATEGORY_ATS_PARSE}


def test_every_rule_has_a_valid_category() -> None:
    for rule in RULES:
        assert rule.category in _VALID_CATEGORIES, rule.rule_id


def test_findings_are_stamped_with_their_rule_category() -> None:
    # A passive-voice highlight is a writing-category finding.
    resolved = _make_resolved(
        work=[{"company": "Acme", "highlights": ["The API was designed by the team."]}],
    )
    findings = lint(resolved, rule_ids=["wl-001"])
    assert findings
    assert all(f.category == CATEGORY_WRITING for f in findings)


def test_ats_parse_category_on_date_format_rule() -> None:
    resolved = _make_resolved(
        work=[
            {"company": "A", "title": "Eng", "start_date": "2021-03", "end_date": "2022"},
            {"company": "B", "title": "Eng", "start_date": "2019", "end_date": "2020-01"},
        ],
    )
    findings = lint(resolved, rule_ids=["wl-012"])
    assert findings
    assert all(f.category == CATEGORY_ATS_PARSE for f in findings)


def test_category_counts_covers_all_axes() -> None:
    counts = category_counts([])
    assert counts == {
        CATEGORY_WRITING: 0,
        CATEGORY_STRUCTURE: 0,
        CATEGORY_ATS_PARSE: 0,
    }


# ── wl-018: education size ───────────────────────────────────────────


def _education(n: int) -> list[dict]:
    return [
        {"institution": f"Inst {i}", "degree": "Course", "start_date": "2020"} for i in range(n)
    ]


def test_wl018_flags_oversized_education() -> None:
    resolved = make_resolved(education=_education(23))
    findings = lint(resolved, rule_ids=["wl-018"])
    assert len(findings) == 1
    assert "23 education entries" in findings[0].message
    assert "certifications.yaml" in findings[0].fix_hint
    assert findings[0].category == "structure"


def test_wl018_silent_at_threshold() -> None:
    assert lint(make_resolved(education=_education(6)), rule_ids=["wl-018"]) == []


def test_wl018_skipped_when_education_hidden() -> None:
    resolved = make_resolved(
        education=_education(23),
        show={"work": True, "education": False, "skills": True, "projects": True},
    )
    assert lint(resolved, rule_ids=["wl-018"]) == []
