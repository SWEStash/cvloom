"""Tests for the overlay system."""

from __future__ import annotations

import copy
from typing import Any

from cvloom.loader import flatten_highlights, normalize_highlights
from cvloom.overlays import apply_overlays, validate_overlays

# ── Helpers ──────────────────────────────────────────────────────


def _base_data() -> dict[str, Any]:
    """Return a minimal base data dict with normalized highlights."""
    return {
        "basics": {
            "headline": "Software Engineer",
            "summary": "A capable engineer.",
        },
        "work": [
            {
                "company": "Acme Corp",
                "title": "Senior Backend Engineer",
                "start_date": "2021-03",
                "highlights": [
                    {"id": "migration", "text": "Led migration."},
                    {"id": "kafka", "text": "Designed Kafka pipeline."},
                    {"id": "mentoring", "text": "Mentored juniors."},
                ],
                "tags": ["python", "kafka"],
            },
            {
                "company": "Previous Inc",
                "title": "Software Engineer",
                "start_date": "2018-06",
                "highlights": [
                    {"id": "rest-api", "text": "Built REST API."},
                    {"id": "latency", "text": "Reduced latency."},
                ],
                "tags": ["python", "fastapi"],
            },
        ],
        "education": [
            {
                "institution": "State University",
                "degree": "BSc",
                "start_date": "2014",
                "highlights": [
                    {"id": "gpa", "text": "GPA 3.8/4.0"},
                ],
            },
        ],
        "projects": [
            {
                "name": "side-project",
                "description": "A side project.",
                "tags": ["python"],
                "highlights": [
                    {"id": "oss", "text": "Open source."},
                ],
            },
            {
                "name": "tool",
                "description": "A useful tool.",
                "tags": ["go"],
                "highlights": [],
            },
        ],
        "skills": [
            {"category": "Languages", "items": ["Python", "Go", "TypeScript"]},
            {"category": "Frameworks & Libraries", "items": ["FastAPI", "Django"]},
            {"category": "Data & Messaging", "items": ["PostgreSQL", "Kafka"]},
            {"category": "Infrastructure & Cloud", "items": ["AWS", "Docker"]},
        ],
    }


# ── Basics overlay ───────────────────────────────────────────────


class TestBasicsOverlay:
    def test_shallow_merge(self):
        data = _base_data()
        profile = {
            "overlays": {
                "basics": {
                    "headline": "Infra Engineer",
                    "summary": "New summary.",
                }
            }
        }
        apply_overlays(data, profile)
        assert data["basics"]["headline"] == "Infra Engineer"
        assert data["basics"]["summary"] == "New summary."

    def test_partial_merge_preserves_other_keys(self):
        data = _base_data()
        profile = {"overlays": {"basics": {"headline": "Changed"}}}
        apply_overlays(data, profile)
        assert data["basics"]["headline"] == "Changed"
        assert data["basics"]["summary"] == "A capable engineer."


# ── Work / array overlay ────────────────────────────────────────


class TestArrayOverlay:
    def test_pick_highlights(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "highlights": {
                            "mode": "pick",
                            "items": ["kafka"],
                        },
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        acme = data["work"][0]
        assert len(acme["highlights"]) == 1
        assert acme["highlights"][0]["id"] == "kafka"

    def test_exclude_highlights(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "highlights": {
                            "mode": "exclude",
                            "items": ["mentoring"],
                        },
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        acme = data["work"][0]
        assert len(acme["highlights"]) == 2
        ids = [h["id"] for h in acme["highlights"]]
        assert "mentoring" not in ids

    def test_append_highlights(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "highlights": {
                            "mode": "all",
                            "append": ["Extra bullet point."],
                        },
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        acme = data["work"][0]
        assert len(acme["highlights"]) == 4
        assert acme["highlights"][-1]["text"] == "Extra bullet point."

    def test_replace_highlights(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "highlights": {
                            "mode": "all",
                            "replace": {"kafka": "Rewrote Kafka pipeline."},
                        },
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        acme = data["work"][0]
        kafka_hl = [h for h in acme["highlights"] if h["id"] == "kafka"][0]
        assert kafka_hl["text"] == "Rewrote Kafka pipeline."

    def test_pick_and_append(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "highlights": {
                            "mode": "pick",
                            "items": ["kafka"],
                            "append": ["Bonus."],
                        },
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        acme = data["work"][0]
        assert len(acme["highlights"]) == 2
        assert acme["highlights"][0]["id"] == "kafka"
        assert acme["highlights"][1]["text"] == "Bonus."

    def test_exclude_entry(self):
        data = _base_data()
        profile = {
            "overlays": {
                "projects": [
                    {
                        "match": {"name": "side-project"},
                        "exclude": True,
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        names = [p["name"] for p in data["projects"]]
        assert "side-project" not in names
        assert "tool" in names

    def test_unmatched_overlay_warns(self, capsys):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Nonexistent Corp"},
                        "highlights": {"mode": "all"},
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        # Warning goes to stderr via Rich — just check no crash

    def test_multi_field_match(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {
                            "company": "Acme Corp",
                            "title": "Senior Backend Engineer",
                        },
                        "highlights": {"mode": "pick", "items": ["migration"]},
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        acme = data["work"][0]
        assert len(acme["highlights"]) == 1

    def test_education_overlay(self):
        data = _base_data()
        profile = {
            "overlays": {
                "education": [
                    {
                        "match": {"institution": "State University"},
                        "highlights": {
                            "mode": "all",
                            "append": ["Dean's list 2016."],
                        },
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        edu = data["education"][0]
        assert len(edu["highlights"]) == 2

    def test_title_override(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "title": "Lead Infrastructure Engineer",
                    }
                ]
            }
        }
        apply_overlays(data, profile)
        assert data["work"][0]["title"] == "Lead Infrastructure Engineer"


# ── Skills overlay ───────────────────────────────────────────────


class TestSkillsOverlay:
    def test_include_categories(self):
        data = _base_data()
        profile = {
            "overlays": {
                "skills": {
                    "include_categories": ["Languages", "Data & Messaging"],
                }
            }
        }
        apply_overlays(data, profile)
        cats = [s["category"] for s in data["skills"]]
        assert cats == ["Languages", "Data & Messaging"]

    def test_exclude_categories(self):
        data = _base_data()
        profile = {
            "overlays": {
                "skills": {
                    "exclude_categories": ["Frameworks & Libraries"],
                }
            }
        }
        apply_overlays(data, profile)
        cats = [s["category"] for s in data["skills"]]
        assert "Frameworks & Libraries" not in cats
        assert len(cats) == 3

    def test_category_override_exclude_items(self):
        data = _base_data()
        profile = {
            "overlays": {
                "skills": {
                    "category_overrides": {
                        "Languages": {"exclude_items": ["TypeScript"]},
                    }
                }
            }
        }
        apply_overlays(data, profile)
        langs = [s for s in data["skills"] if s["category"] == "Languages"][0]
        assert "TypeScript" not in langs["items"]
        assert "Python" in langs["items"]

    def test_include_plus_override(self):
        data = _base_data()
        profile = {
            "overlays": {
                "skills": {
                    "include_categories": ["Languages"],
                    "category_overrides": {
                        "Languages": {"exclude_items": ["Go"]},
                    },
                }
            }
        }
        apply_overlays(data, profile)
        assert len(data["skills"]) == 1
        assert "Go" not in data["skills"][0]["items"]


# ── Highlight normalization / flattening ─────────────────────────


class TestHighlightNormalization:
    def test_normalize_strings(self):
        entries = [{"highlights": ["one", "two"]}]
        normalize_highlights(entries)
        assert entries[0]["highlights"] == [
            {"id": None, "text": "one"},
            {"id": None, "text": "two"},
        ]

    def test_normalize_objects(self):
        entries = [{"highlights": [{"id": "a", "text": "Alpha"}]}]
        normalize_highlights(entries)
        assert entries[0]["highlights"] == [{"id": "a", "text": "Alpha"}]

    def test_normalize_mixed(self):
        entries = [{"highlights": ["plain", {"id": "x", "text": "X"}]}]
        normalize_highlights(entries)
        assert entries[0]["highlights"][0] == {"id": None, "text": "plain"}
        assert entries[0]["highlights"][1] == {"id": "x", "text": "X"}

    def test_flatten(self):
        entries = [
            {
                "highlights": [
                    {"id": "a", "text": "Alpha"},
                    {"id": None, "text": "Beta"},
                ]
            }
        ]
        flatten_highlights(entries)
        assert entries[0]["highlights"] == ["Alpha", "Beta"]

    def test_no_highlights_key(self):
        entries = [{"company": "Foo"}]
        normalize_highlights(entries)
        flatten_highlights(entries)
        assert "highlights" not in entries[0]

    def test_roundtrip(self):
        entries = [{"highlights": ["one", {"id": "two", "text": "Two"}]}]
        normalize_highlights(entries)
        flatten_highlights(entries)
        assert entries[0]["highlights"] == ["one", "Two"]


# ── No overlays = no-op ─────────────────────────────────────────


class TestNoOverlays:
    def test_empty_profile(self):
        data = _base_data()
        original = copy.deepcopy(data)
        apply_overlays(data, {})
        assert data == original

    def test_profile_without_overlays(self):
        data = _base_data()
        original = copy.deepcopy(data)
        apply_overlays(data, {"template": "cv/ats-single"})
        assert data == original


# ── Validate overlays ────────────────────────────────────────────


class TestValidateOverlays:
    def test_no_warnings_for_valid(self):
        data = _base_data()
        profile = {
            "overlays": {
                "skills": {"include_categories": ["Languages"]},
            }
        }
        warnings = validate_overlays(data, profile)
        assert warnings == []

    def test_warns_mutually_exclusive_skills(self):
        data = _base_data()
        profile = {
            "overlays": {
                "skills": {
                    "include_categories": ["Languages"],
                    "exclude_categories": ["Frameworks"],
                },
            }
        }
        warnings = validate_overlays(data, profile)
        assert any("mutually exclusive" in w for w in warnings)

    def test_warns_unmatched_work_overlay(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [{"match": {"company": "NonExistent"}}],
            }
        }
        warnings = validate_overlays(data, profile)
        assert any("does not match any entry" in w for w in warnings)

    def test_warns_unmatched_project_overlay(self):
        data = _base_data()
        profile = {
            "overlays": {
                "projects": [{"match": {"name": "NonExistent"}}],
            }
        }
        warnings = validate_overlays(data, profile)
        assert any("does not match any entry" in w for w in warnings)

    def test_no_warning_when_matched(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [{"match": {"company": "Acme Corp"}}],
            }
        }
        warnings = validate_overlays(data, profile)
        assert not any("does not match" in w for w in warnings)

    def test_warns_nonexistent_highlight_id_pick(self):
        data = _base_data()
        # Normalize highlights to {id, text} format for ID checking
        for entry in data["work"]:
            for i, h in enumerate(entry.get("highlights", [])):
                if isinstance(h, str):
                    entry["highlights"][i] = {"id": f"h{i}", "text": h}
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "highlights": {"mode": "pick", "items": ["nonexistent"]},
                    }
                ],
            }
        }
        warnings = validate_overlays(data, profile)
        assert any("highlight ID 'nonexistent' not found" in w for w in warnings)

    def test_warns_nonexistent_replace_id(self):
        data = _base_data()
        for entry in data["work"]:
            for i, h in enumerate(entry.get("highlights", [])):
                if isinstance(h, str):
                    entry["highlights"][i] = {"id": f"h{i}", "text": h}
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "highlights": {"replace": {"badid": "new text"}},
                    }
                ],
            }
        }
        warnings = validate_overlays(data, profile)
        assert any("replace ID 'badid' not found" in w for w in warnings)

    def test_no_warning_valid_highlight_ids(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [
                    {
                        "match": {"company": "Acme Corp"},
                        "highlights": {"mode": "pick", "items": ["migration"]},
                    }
                ],
            }
        }
        warnings = validate_overlays(data, profile)
        assert not any("not found" in w for w in warnings)

    def test_warns_unknown_match_field(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [{"match": {"company": "Acme Corp", "foo": "bar"}}],
            }
        }
        warnings = validate_overlays(data, profile)
        assert any("unknown match field 'foo'" in w for w in warnings)

    def test_warns_unknown_skill_category(self):
        data = _base_data()
        profile = {
            "overlays": {
                "skills": {"include_categories": ["Nonexistent"]},
            }
        }
        warnings = validate_overlays(data, profile)
        assert any("unknown category 'Nonexistent'" in w for w in warnings)

    def test_warns_unknown_category_override(self):
        data = _base_data()
        profile = {
            "overlays": {
                "skills": {"category_overrides": {"Fake": {"exclude_items": ["x"]}}},
            }
        }
        warnings = validate_overlays(data, profile)
        assert any("unknown category 'Fake'" in w for w in warnings)

    def test_valid_match_fields_no_warning(self):
        data = _base_data()
        profile = {
            "overlays": {
                "work": [{"match": {"company": "Acme Corp", "title": "Engineer"}}],
            }
        }
        warnings = validate_overlays(data, profile)
        assert not any("unknown match field" in w for w in warnings)
