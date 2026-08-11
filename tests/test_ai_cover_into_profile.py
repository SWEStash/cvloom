"""The round trip `ai cover --body-only` exists for.

Before body-only mode the two cover-letter paths could not meet: `ai cover` wrote a
complete letter with its own salutation and sign-off, and the only place to put it
was `job_context.notes`, which `cover-letter/*.html.j2` renders *between* the
greeting and closing it builds from the locale pack. Pasting one into the other
produced two greetings, two closings and two signatures, in possibly two languages.

These tests paste a body-only letter through the real `_notes_block` helper and
build, so they fail if the block stops being valid YAML, if the template starts
supplying furniture the AI is also asked for, or if either drifts out of the pack.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cvloom import builder
from cvloom.cli import _notes_block
from cvloom.locale import load_pack
from tests.conftest import make_project

# Two paragraphs and a blank line between them — the shape a cover letter body has,
# and the shape that breaks a YAML block written with the wrong indent.
_BODY = (
    "I have spent the last six years building payment infrastructure, and the "
    "ingestion work you describe is the part of that I would choose again.\n"
    "\n"
    "At Acme I owned the pipeline end to end, which is the closest thing I have "
    "to the problem in your posting."
)


def _letter_project(tmp_path: Path, body: str, *, extra: dict[str, str] | None = None) -> Path:
    """A project whose `letter` profile carries *body* as pasted notes."""
    profile = "template: cover-letter/standard\njob_context:\n  company: Acme\n"
    # The block is emitted at top level, so its `job_context:` key merges with the
    # one above only if the user pastes it there. Splicing the two here mirrors
    # what the printed instruction tells them to do.
    pasted = _notes_block(body).removeprefix("job_context:\n")
    return make_project(
        tmp_path, extra={"profiles/letter.yaml": profile + pasted + "\n", **(extra or {})}
    )


def _html(root: Path) -> str:
    return builder.build_project(root, profile_name="letter", public=True, skip_pdf=True).html


def test_a_pasted_body_renders_exactly_one_of_each_piece_of_furniture(tmp_path: Path) -> None:
    """AC5. Counting, not presence: the bug was duplication, not absence."""
    html = _html(_letter_project(tmp_path, _BODY))
    pack, _ = load_pack("en")
    assert html.count(pack.cover_letter["greeting"]) == 1
    assert html.count(pack.cover_letter["closing"]) == 1
    assert html.count('class="sig-name"') == 1


def test_both_paragraphs_survive_the_paste(tmp_path: Path) -> None:
    """A block indented wrong loses the second paragraph rather than erroring."""
    html = _html(_letter_project(tmp_path, _BODY))
    assert "payment infrastructure" in html
    assert "owned the pipeline end to end" in html
    # `md` renders the blank line as a paragraph break rather than one run-on line.
    assert html.count("<p>") >= 2


def test_the_furniture_is_the_projects_language_not_the_letters(tmp_path: Path) -> None:
    """The body is English and the project is Spanish; the pack wins, because the
    template — not the model — is what renders these three strings."""
    root = _letter_project(tmp_path, _BODY, extra={"cvloom.yaml": "locale: es\n"})
    html = _html(root)
    pack, _ = load_pack("es")
    assert f"{pack.cover_letter['greeting']} {pack.cover_letter['fallback_salutee']}," in html
    assert pack.cover_letter["closing"] in html
    for english in ("Dear", "Hiring Manager", "Sincerely"):
        assert english not in html


@pytest.mark.parametrize("body", ["single line body", _BODY, "  leading and trailing  "])
def test_the_notes_block_is_valid_yaml_for_any_body_shape(tmp_path: Path, body: str) -> None:
    """The helper's output is pasted into a file cvloom never validates for the
    user, so a malformed block surfaces as a resolve error days later."""
    html = _html(_letter_project(tmp_path, body))
    assert body.strip().splitlines()[0].strip() in html
