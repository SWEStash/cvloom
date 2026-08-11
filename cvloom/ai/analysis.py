"""The deterministic half of what cvloom knows, rendered for a prompt.

`review` and `suggest` used to receive the CV text and nothing else, so the model
guessed at what 25 lint rules answer exactly and could not see what no amount of
reading the CV would reveal — that it renders to four pages, or that its template
interleaves columns when an ATS reads the text layer. `align` already fed
`MatchReport` into a `<keyword_analysis>` block; this generalises that shape to
everything else cvloom computes.

**The block is written in English even for a Spanish project.** Instruction-space
is English throughout the prompt layer; the language of the *answer* is set by
`prompts.locale_context_block`. Finding messages carry the CV's own words inside
them, so a Spanish bullet still reaches the model in Spanish — quoted, as data.

**Size is the safety mechanism, not just a quality one.** Ollama drops the *front*
of an over-long prompt, and the grounding contract lives in the system message, so
an oversized block does not merely crowd out the CV — it can push the
anti-fabrication rules out of the request entirely. Hence a budget expressed as a
fraction of the CV, and a downward walk through progressively coarser renderings
rather than a single fixed layout.

Measured on the repo's own demo projects, `scope=full` (2026-08-10)::

    project        cv_to_text   findings   budget   level     rules shown
    examples/      2593 chars   22         1555     grouped   3 of 7 groups
    examples-es/   1727 chars    1         1036     grouped   1 of 1

Ratios were fitted to those numbers, not invented. At 1.0 the whole naive block
is admitted and reproduces the crowd-out this exists to prevent; at 0.3
`examples/` drops to `compact` and loses every `fix_hint` — the part the model
most needs in order to judge whether a finding is worth acting on. 0.6 keeps the
hints and sheds the lowest-priority groups instead, which is the trade the
`not shown:` line exists to make visible.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from cvloom import linter, linter_locales, sections, templates_meta, trim
from cvloom.models import ResolvedProfile

SCOPE_FULL = "full"
"""`review`, `suggest` — can act on any finding, down to a single bullet."""

SCOPE_BRIEF = "brief"
"""`align` — can act on shape, length and the aggregate tone the writing rules
imply, but not on the wording of one bullet."""

SCOPE_EVIDENCE = "evidence"
"""`cover` — needs to know what to lead with, not what is wrong.

A cover-letter generator can do nothing with a weak-verb finding, and feeding it
"No quantified outcome in this entry" at temperature 0.7 is an active invitation
to supply the missing number itself. So this scope carries no defect findings at
all: it reports length pressure, parse risk, and the *inverse* of the
quantification rule — which entries already carry a metric worth leading with.
"""

LEVEL_GROUPED = "grouped"
LEVEL_COMPACT = "compact"
LEVEL_COUNTS = "counts"

_SEVERITY_RANK = {"warning": 0, "suggestion": 1, "info": 2}
_CATEGORY_RANK = {
    linter.CATEGORY_ATS_PARSE: 0,
    linter.CATEGORY_STRUCTURE: 1,
    linter.CATEGORY_WRITING: 2,
}
_QUANTIFICATION_RULE = "wl-002"
_QUANTIFIED_SECTIONS = ("work", "projects")
"""The sections wl-002 examines. Inverting a rule means inverting it over the same
entries the rule looked at — a skills category is neither quantified nor flagged."""
_MAX_INSTANCES_PER_RULE = 3
_TOP_WRITING_RULES = 3
_BUDGET_RATIO = {SCOPE_FULL: 0.6, SCOPE_BRIEF: 0.2, SCOPE_EVIDENCE: 0.2}
_BUDGET_FLOOR = 600
_WRAPPER_CHARS = len("<analysis>\n\n</analysis>")
_MAX_QUANTIFIED_ENTRIES = 12

_PREAMBLE = (
    "Deterministic checks cvloom already ran on this CV. These are facts produced by "
    "rules, not opinions: do not re-derive them and do not list them back. Judge which "
    "of them actually matter for this candidate and this target, and see what rules cannot."
)


@dataclass(frozen=True)
class AnalysisBlock:
    """A rendered `<analysis>` block plus what had to be given up to fit it."""

    text: str

    level: str
    """How much per-finding detail survived. Always ``counts`` for the two narrow
    scopes, which never render instances by design."""

    findings_total: int
    findings_shown: int

    budget_chars: int
    """The size the sheddable detail was fitted to. Bounds ``text`` for
    ``SCOPE_FULL``; for the narrow scopes the header alone may exceed it, since
    there is nothing there to shed."""

    notes: tuple[str, ...]
    """Empty unless something was given up. The per-rule instance cap is the
    normal rendering and does not count — only shed groups and a drop to a
    coarser level do, so a healthy run shows the user no notice at all."""


@dataclass(frozen=True)
class _Group:
    """One rule's findings, keyed by rule and hint.

    Keyed on `(rule_id, fix_hint)` rather than `rule_id` alone because a rule can
    carry more than one hint — `wl-016` does — and collapsing those would attach
    one rule's advice to another rule's findings.
    """

    rule_id: str
    fix_hint: str
    severity: str
    category: str
    findings: tuple[linter.LintFinding, ...]


# ── Sorting ─────────────────────────────────────────────────────────


def _instance_key(finding: linter.LintFinding) -> tuple[int, str, int]:
    """Document order, so the block reads in the order the reader's CV does."""
    order = sections.DEFAULT_SECTION_ORDER
    position = order.index(finding.section) if finding.section in order else len(order)
    return (
        position,
        finding.entry,
        finding.bullet_index if finding.bullet_index is not None else -1,
    )


def _group_key(group: _Group) -> tuple[int, int, int, str]:
    """Most severe first, then most likely to make the CV unreadable by machine.

    An `ats-parse` finding means a system may not read the line at all, which
    outranks any judgement about how well it is written.
    """
    return (
        _SEVERITY_RANK.get(group.severity, len(_SEVERITY_RANK)),
        _CATEGORY_RANK.get(group.category, len(_CATEGORY_RANK)),
        -len(group.findings),
        group.rule_id,
    )


def _groups(findings: list[linter.LintFinding]) -> list[_Group]:
    buckets: dict[tuple[str, str], list[linter.LintFinding]] = {}
    for finding in findings:
        buckets.setdefault((finding.rule_id, finding.fix_hint), []).append(finding)
    groups = [
        _Group(
            rule_id=rule_id,
            fix_hint=fix_hint,
            severity=members[0].severity,
            category=members[0].category,
            findings=tuple(sorted(members, key=_instance_key)),
        )
        for (rule_id, fix_hint), members in buckets.items()
    ]
    return sorted(groups, key=_group_key)


# ── Header lines ────────────────────────────────────────────────────


def _locale_line(resolved: ResolvedProfile) -> str:
    code = resolved.locale.code
    active, skipped = linter.rules_for(code)
    line = f"locale: {code} — {len(active)} of {len(active) + len(skipped)} lint rules ran"
    if skipped:
        names = ", ".join(rule.rule_id for rule in skipped)
        # Naming them matters most where coverage is thinnest: "no readability
        # finding" must not read as "readable" when the readability rule never ran.
        line += f" ({names} ha{'s' if len(skipped) == 1 else 've'} no {code} implementation)"
    return line


def _length_line(report: trim.TrimReport) -> str:
    pages = "1 page" if report.estimated_pages == 1 else f"{report.estimated_pages} pages"
    line = (
        f"length: {report.total_words} words, about {pages} "
        f"against a {report.target_pages}-page target"
    )
    if report.words_to_cut > 0:
        line += f" — roughly {report.words_to_cut} words over"
    return line


def _template_line(template_name: str) -> str:
    info = templates_meta.info_for(template_name)
    if info is None:
        return f"template: {template_name} — not a packaged template; parse risk unknown"
    columns = "1 column" if info.columns == 1 else f"{info.columns} columns"
    line = f'template: {template_name} — {columns}, PDF text extraction rated "{info.ats}"'
    if info.caveat:
        line += f".\n  {info.caveat}"
    return line


def _findings_line(findings: list[linter.LintFinding]) -> str:
    counts = linter.category_counts(findings)
    breakdown = ", ".join(f"{name} {count}" for name, count in counts.items() if count)
    return f"findings: {len(findings)}" + (f" ({breakdown})" if breakdown else "")


def _header(resolved: ResolvedProfile, findings: list[linter.LintFinding]) -> str:
    return "\n".join(
        [
            _PREAMBLE,
            "",
            _locale_line(resolved),
            _length_line(trim.analyze(resolved)),
            _template_line(resolved.template_name),
            _findings_line(findings),
        ]
    )


# ── Renderings, coarsest last ───────────────────────────────────────


def _instance(finding: linter.LintFinding) -> str:
    where = f"{finding.section} / {finding.entry}" if finding.entry else finding.section
    if finding.bullet_index is not None:
        where += f", bullet {finding.bullet_index + 1}"
    return f"  - {where}: {finding.message}"


def _render_grouped(header: str, groups: list[_Group], budget: int) -> tuple[str, int, list[str]]:
    """Per-rule hint plus a few instances each, shedding whole groups to fit."""
    lines = [header]
    shown = 0
    dropped: list[_Group] = []
    for index, group in enumerate(groups):
        block = [
            "",
            f"{group.rule_id} [{group.category}/{group.severity}] x{len(group.findings)} "
            f"— fix: {group.fix_hint}",
        ]
        kept = group.findings[:_MAX_INSTANCES_PER_RULE]
        block += [_instance(f) for f in kept]
        if len(group.findings) > len(kept):
            block.append(f"  ... and {len(group.findings) - len(kept)} more of {group.rule_id}")
        candidate = "\n".join([*lines, *block])
        if len(candidate) > budget and index > 0:
            dropped = groups[index:]
            break
        lines += block
        shown += len(kept)
    notes: list[str] = []
    if dropped:
        # Merged by rule id: a rule with two distinct hints is two groups, but a
        # reader counting "wl-016 x5, wl-016 x1" learns nothing the merged form does
        # not say better.
        tally: Counter[str] = Counter()
        for group in dropped:
            tally[group.rule_id] += len(group.findings)
        summary = ", ".join(f"{rule_id} x{count}" for rule_id, count in sorted(tally.items()))
        lines += ["", f"not shown: {summary}"]
        notes.append(
            f"{sum(len(g.findings) for g in dropped)} lower-priority lint findings were "
            "left out of the AI context to keep the CV itself in the prompt."
        )
    return "\n".join(lines), shown, notes


def _render_compact(
    header: str, findings: list[linter.LintFinding], budget: int
) -> tuple[str, int, list[str]]:
    """One line per finding, no hints — the level at which the model can still see
    every problem but has to work out the fix for itself."""
    ordered = sorted(
        findings,
        key=lambda f: (_SEVERITY_RANK.get(f.severity, len(_SEVERITY_RANK)), _instance_key(f)),
    )
    lines = [header, ""]
    shown = 0
    for finding in ordered:
        where = f"{finding.section} / {finding.entry}" if finding.entry else finding.section
        tag = f"[{finding.category}/{finding.severity}]"
        line = f"{finding.rule_id} {tag} {where}: {finding.message}"
        if len("\n".join([*lines, line])) > budget:
            break
        lines.append(line)
        shown += 1
    if shown < len(ordered):
        lines.append(f"... and {len(ordered) - shown} more")
    return (
        "\n".join(lines),
        shown,
        ["Lint findings were reduced to one line each to fit the model's context."],
    )


def _render_counts(header: str, findings: list[linter.LintFinding]) -> tuple[str, int, list[str]]:
    """The floor, not a graceful landing: counts alone give the model nothing to
    act on, so reaching this level is worth telling the user about."""
    tally = Counter(f.rule_id for f in findings)
    summary = ", ".join(f"{rule_id} x{count}" for rule_id, count in sorted(tally.items()))
    lines = [header, "", f"findings by rule: {summary or 'none'}"]
    return (
        "\n".join(lines),
        0,
        [
            "The CV is long enough that only lint finding *counts* fit alongside it. "
            "The AI cannot act on individual findings — run `cvloom check` for those."
        ],
    )


# ── Scope-specific extras ───────────────────────────────────────────


def _quantified_entries(resolved: ResolvedProfile, findings: list[linter.LintFinding]) -> str:
    """Which entries already carry a metric, derived from the *absence* of wl-002.

    Stated as evidence to lead with rather than as a gap to fill, which is the
    whole reason `cover` can be given it: "these lack metrics" is a prompt for a
    creative model to invent one.
    """
    unquantified = {(f.section, f.entry) for f in findings if f.rule_id == _QUANTIFICATION_RULE}
    quantified: list[str] = []
    for name in _QUANTIFIED_SECTIONS:
        if not resolved.show_sections.get(name):
            continue
        for entry in resolved.data.get(name) or []:
            # An entry with no highlights is not flagged by the rule and is not
            # evidence either, so the inverse skips it the same way the rule does.
            # Otherwise every bare entry reads as a quantified achievement.
            if not entry.get("highlights"):
                continue
            label = sections.entry_label(name, entry)
            if (name, label) in unquantified or f"{name}/{label}" in quantified:
                continue
            quantified.append(f"{name}/{label}")
    if not quantified:
        return "entries with a quantified outcome: none — lead on scope and responsibility instead"
    shown = quantified[:_MAX_QUANTIFIED_ENTRIES]
    line = "entries with a quantified outcome: " + ", ".join(shown)
    if len(quantified) > len(shown):
        line += f", and {len(quantified) - len(shown)} more"
    return line


_WEAK_OPENER_RULE = "wl-004"


def _weak_opener_constraint(resolved: ResolvedProfile) -> str:
    """Name the openers wl-004 will flag, so a rewrite does not land on another one.

    Without this the model is told *this* opener is weak and never told what the
    full set is, so it rewrites `was responsible for` into `participated in`, the
    finding fires again on the bullet it just fixed, and cvloom contradicts itself
    in front of the user.

    Only the constraint set is sent, never `strong_verb_examples`. Sharing the
    rubric leaves the vocabulary open; supplying five verbs to use instead is what
    collapses every generated bullet onto the same five words — the same reason
    wl-004's own fix hint stopped naming them.

    The phrases are quoted in the CV's language while the sentence around them
    stays English, matching how finding messages already carry Spanish bullets
    into an English block.
    """
    openers = linter_locales.pack_for(resolved.locale.code).weak_openers
    quoted = ", ".join(f'"{opener}"' for opener in openers)
    return (
        f"openers {_WEAK_OPENER_RULE} will flag again — avoid starting a bullet with "
        f"any of them: {quoted}. Any other verb is yours to choose."
    )


def _writing_tone(findings: list[linter.LintFinding]) -> str:
    """The aggregate the writing rules imply, without pointing at any one bullet."""
    tally = Counter(f.rule_id for f in findings if f.category == linter.CATEGORY_WRITING)
    if not tally:
        return "writing rules: nothing flagged"
    top = tally.most_common(_TOP_WRITING_RULES)
    return "most frequent writing findings: " + ", ".join(f"{r} x{n}" for r, n in top)


# ── Entry point ─────────────────────────────────────────────────────


def analysis_context_block(
    resolved: ResolvedProfile, cv_text: str, *, scope: str = SCOPE_FULL
) -> AnalysisBlock:
    """Render what cvloom's own checks already know about *resolved*.

    *cv_text* is passed rather than recomputed: the caller already holds it, and
    the size budget is a fraction of it. Characters, not tokens — the block and
    the CV are in the same language, so the tokenizer's bias cancels between
    numerator and denominator, which is not true of an absolute limit.
    """
    findings = linter.lint(resolved)
    budget = max(_BUDGET_FLOOR, int(_BUDGET_RATIO[scope] * len(cv_text)))
    body_budget = budget - _WRAPPER_CHARS
    header = _header(resolved, findings)

    # The two narrow scopes have no per-finding detail to shed, so they render
    # once. The header is unconditional there — length and parse risk are the
    # whole point of giving them a block at all — which is why `budget_chars` is
    # a bound on the sheddable detail rather than on the string.
    if scope in (SCOPE_BRIEF, SCOPE_EVIDENCE):
        extras = [_quantified_entries(resolved, findings)]
        if scope == SCOPE_BRIEF:
            extras.append(_writing_tone(findings))
        return _wrap("\n".join([header, "", *extras]), LEVEL_COUNTS, len(findings), 0, budget, ())

    # A downward walk, not a computation: each rendering is a pure function, and
    # the first one that fits wins. `counts` is the floor rather than a landing —
    # it leaves the model nothing to act on, which is why it always emits a note.
    level = LEVEL_GROUPED
    text, shown, notes = _render_grouped(header, _groups(findings), body_budget)
    if len(text) > body_budget:
        level = LEVEL_COMPACT
        text, shown, notes = _render_compact(header, findings, body_budget)
    if len(text) > body_budget:
        level = LEVEL_COUNTS
        text, shown, notes = _render_counts(header, findings)

    # Appended after the walk, and gated on the rendered text rather than on
    # `findings`: if shedding dropped the wl-004 group, the constraint would be a
    # rule the model is told to obey with nothing above it explaining why. Being
    # outside the budget is deliberate for the same reason the header is — this
    # is not detail to shed, and it is one line.
    if _WEAK_OPENER_RULE in text:
        text += "\n\n" + _weak_opener_constraint(resolved)

    return _wrap(text, level, len(findings), shown, budget, tuple(notes))


def _wrap(
    body: str,
    level: str,
    total: int,
    shown: int,
    budget: int,
    notes: tuple[str, ...],
) -> AnalysisBlock:
    return AnalysisBlock(
        text=f"<analysis>\n{body}\n</analysis>",
        level=level,
        findings_total=total,
        findings_shown=shown,
        budget_chars=budget,
        notes=notes,
    )
