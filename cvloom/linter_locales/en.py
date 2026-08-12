"""English linter data.

Lifted out of ``linter.py`` unchanged — this module is the `en` half of the
extraction, and the existing linter tests are its correctness proof.
"""

from __future__ import annotations

import re

from cvloom.linter_locales import LintLocale

# ── wl-001: passive voice ───────────────────────────────────────────

# Auxiliary + past participle.
_PASSIVE = re.compile(
    r"\b(?:was|were|been|being|is|are)\s+"
    r"(?:also\s+)?"
    r"([a-z]+(?:ed|en|wn|lt|ht|pt|nt))\b",
    re.IGNORECASE,
)

# Words matching the participle shape that are adjectives, not participles.
_PASSIVE_FALSE_POSITIVES = frozenset(
    {
        "present",
        "recent",
        "absent",
        "current",
        "different",
        "important",
        "efficient",
        "excellent",
        "sufficient",
        "consistent",
        "persistent",
        "resilient",
        "intelligent",
        "confident",
        "competent",
        "relevant",
        "elegant",
        "frequent",
        "urgent",
        "ancient",
        "silent",
        "content",
        "evident",
        "dependent",
        "independent",
        "spent",
        "sent",
        "went",
        "bent",
        "lent",
        "meant",
        "dealt",
        "felt",
        "built",
        "knelt",
        "prevalent",
        "prominent",
        "transparent",
        "coherent",
        "concurrent",
        "existent",
        "inherent",
        "latent",
        "potent",
        "reluctant",
        "apparent",
        "brilliant",
        "compliant",
        "diligent",
        "proficient",
        "emergent",
        "equivalent",
        "fluent",
    }
)

# ── wl-003: noise skills ────────────────────────────────────────────

_NOISE_SKILLS = frozenset(
    {
        "microsoft office",
        "microsoft word",
        "microsoft excel",
        "microsoft powerpoint",
        "google docs",
        "google sheets",
        "google slides",
        "ms office",
        "ms word",
    }
)

# ── wl-004: weak openers ────────────────────────────────────────────

_WEAK_OPENERS = (
    "helped",
    "assisted",
    "worked on",
    "was responsible for",
    "participated in",
    "was involved in",
)
"""Openers that describe involvement rather than what the candidate produced.

Sourced entry by entry rather than inherited; see wl-004 in
`docs/reference/ats-linter-rules.md` for what backs each one and what does not.
`contributed to` was removed here: no career-office guidance names it, and it is
the accurate word for genuine team work, so flagging it pushed users toward
claiming sole credit — against this project's own position that a weak but true
CV beats a strong invented one.
"""

_STRONG_VERB_EXAMPLES = ("Designed", "Implemented", "Reduced", "Delivered", "Architected")

# ── wl-007: first person ────────────────────────────────────────────

# "I" is case-sensitive: lowercase "i" is never the pronoun, and matching it
# case-insensitively turned every stray initial into a finding. It is kept
# separate from the rest because a bare "I" also needs the roman-numeral
# heuristic in ``linter._has_first_person_en``.
_FIRST_PERSON = re.compile(r"\b(?:my|me|mine|myself)\b", re.IGNORECASE)
PRONOUN_I = re.compile(r"\bI\b")

# ── wl-008: vague buzzwords ─────────────────────────────────────────

_BUZZWORDS = re.compile(
    r"\b(?:"
    r"motivated|detail-oriented|team player|hardworking|"
    r"passionate|dynamic|results-driven|go-getter|"
    r"synergy|proactive|self-starter|innovative"
    r")\b",
    re.IGNORECASE,
)

# ── wl-013: tense (English-only rule implementation) ────────────────

# Present-tense verbs whose -ed ending makes the past-tense heuristic misfire.
PRESENT_TENSE_ED = frozenset(
    {
        "embed",
        "exceed",
        "proceed",
        "succeed",
        "precede",
        "concede",
        "recede",
        "feed",
        "need",
        "breed",
        "speed",
        "seed",
        "heed",
        "bleed",
        "plead",
        "spread",
        "shed",
    }
)

IRREGULAR_PAST = frozenset(
    {
        "led",
        "built",
        "ran",
        "wrote",
        "grew",
        "drove",
        "won",
        "taught",
        "brought",
        "became",
        "came",
        "cut",
        "drew",
        "went",
        "had",
        "held",
        "kept",
        "lost",
        "made",
        "met",
        "paid",
        "put",
        "read",
        "said",
        "sat",
        "sold",
        "took",
        "told",
        "thought",
        "set",
        "got",
        "left",
        "sent",
        "spent",
        "began",
        "broke",
        "chose",
        "found",
        "gave",
        "knew",
        "saw",
        "spoke",
        "stood",
        "wore",
    }
)

PRESENT_TENSE_VERBS = frozenset(
    {
        "design",
        "develop",
        "build",
        "lead",
        "manage",
        "implement",
        "create",
        "write",
        "run",
        "analyze",
        "architect",
        "deploy",
        "maintain",
        "optimize",
        "own",
        "deliver",
        "drive",
        "grow",
        "scale",
        "migrate",
        "integrate",
        "coordinate",
        "mentor",
        "review",
        "define",
        "establish",
        "improve",
        "reduce",
        "increase",
        "support",
        "enable",
        "handle",
        "oversee",
        "operate",
        "automate",
        "monitor",
        "evaluate",
        "collaborate",
    }
)

# ── wl-015: metric and result framing ───────────────────────────────

_RESULT_FRAMING = re.compile(
    r"\b(?:enabling|resulting|achieving|allowing|saving|delivering|"
    r"generating|helping|driving|growing|scaling|improving|"
    r"reducing|increasing|thereby|which|through|via)\b",
    re.IGNORECASE,
)

_METRIC = re.compile(
    r"\d+\s*%|\d+\s*x\b|\$\s*[\d,]+|\d+\s*[kmb]\b",
    re.IGNORECASE,
)

# ── wl-016: readability (English-only rule implementation) ──────────

VOWEL = re.compile(r"[aeiouy]+")
WORD_ALPHA = re.compile(r"\b[a-zA-Z]+\b")
FK_MIN_GRADE = 6
FK_MAX_GRADE = 12

# ── match: stop words ───────────────────────────────────────────────

_JD_MARKERS = (
    "responsibilities",
    "requirements",
    "qualifications",
    "what you'll do",
    "what you will do",
    "what we're looking for",
    "what we are looking for",
    "you'll be",
    "you will be",
    "we're hiring",
    "we are hiring",
    "the role",
    "about the role",
    "years of experience",
    "nice to have",
    "benefits",
    "apply",
    "equal opportunity",
)
"""Phrases a job posting has and a CV, a privacy policy or a README does not.

Matched case-insensitively anywhere in the text, and the bar is one hit — the
check exists to catch a wrong file, not to grade a posting. A real posting that
somehow contains none of these still warns rather than failing, which is why the
list can afford to be short.
"""


_STOP_WORDS = frozenset(
    {
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "did",
        "do",
        "does",
        "doing",
        "don",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "s",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "t",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
    }
)


LOCALE = LintLocale(
    code="en",
    passive_patterns=(_PASSIVE,),
    passive_false_positives=_PASSIVE_FALSE_POSITIVES,
    noise_skills=_NOISE_SKILLS,
    weak_openers=_WEAK_OPENERS,
    strong_verb_examples=_STRONG_VERB_EXAMPLES,
    min_highlight_words=8,
    max_highlight_words=25,
    first_person_pattern=_FIRST_PERSON,
    buzzwords_pattern=_BUZZWORDS,
    min_skills=8,
    max_skills=25,
    words_per_page=500,
    min_summary_words=20,
    max_summary_words=80,
    metric_pattern=_METRIC,
    result_framing_pattern=_RESULT_FRAMING,
    stop_words=_STOP_WORDS,
    jd_markers=_JD_MARKERS,
)
