"""Spanish linter data.

Not a translation of ``en.py``. Three rules needed genuine redesign because a
translated English lexicon would be confidently wrong in Spanish (decision F8),
and the thresholds are scaled by a measured factor rather than a guessed one.

Every list here is deliberately short. A weak-verb list that misfires once
discredits every other finding beside it, so an entry earns its place by being
wrong in real Spanish CV prose, not by being plausible.
"""

from __future__ import annotations

import re

from cvloom.linter_locales import LintLocale

# ── wl-001: passive voice ───────────────────────────────────────────

# Periphrastic passive: ser + participle. The participle is captured so the
# false-positive list works the same way it does in English.
_PASSIVE_PERIPHRASTIC = re.compile(
    r"\b(?:fue|fueron|es|son|será|serán|ha sido|han sido|había sido|habían sido)\s+"
    r"(?:también\s+)?"
    r"(\w+(?:ad[oa]s?|id[oa]s?))\b",
    re.IGNORECASE,
)

# Pasiva refleja: `se implementó`, `se redujeron`. More common than the
# periphrastic form in Spanish professional prose and with no English shape, so
# a ported English rule misses the passive voice that actually appears.
# Restricted to third-person preterite endings, which is where it lands on a CV.
_PASSIVE_REFLEJA = re.compile(
    r"\bse\s+(\w+(?:ó|aron|ieron))\b",
    re.IGNORECASE,
)

_PASSIVE_FALSE_POSITIVES = frozenset(
    {
        # Pronominal, not passive: the `se` belongs to the verb.
        "convirtió",
        "unió",
        "centró",
        "basó",
        "trató",
        "enfocó",
        "dedicó",
        "graduó",
        "especializó",
        "encargó",
        "trasladó",
        "incorporó",
        # Adjectives that end like a participle.
        "rápido",
        "rápida",
        "rápidos",
        "rápidas",
        "válido",
        "válida",
        "sólido",
        "sólida",
        "debido",
        "debida",
        "querido",
        "querida",
    }
)

# ── wl-003: noise skills ────────────────────────────────────────────

_NOISE_SKILLS = frozenset(
    {
        "paquete office",
        "microsoft office",
        "office",
        "ofimática",
        "word",
        "excel",
        "powerpoint",
        "microsoft word",
        "microsoft excel",
        "microsoft powerpoint",
        "correo electrónico",
        "internet",
        "navegación por internet",
        "mecanografía",
    }
)

# ── wl-004: weak openers ────────────────────────────────────────────

# Matched as a prefix of the lowercased bullet, so each entry is the opening of
# a real bullet rather than a bare verb.
_WEAK_OPENERS = (
    "ayudé a",
    "ayudé en",
    "asistí en",
    "participé en",
    "fui responsable de",
    "era responsable de",
    "encargado de",
    "encargada de",
    "trabajé en",
    "formé parte de",
    "estuve involucrado en",
    "estuve involucrada en",
)
"""Longer than the English list because Spanish spells these out more ways, not
because it is a translation of it.

Nine of the twelve have no English counterpart in the list — `era responsable de`
is the imperfect beside the preterite `fui responsable de`, and the two adjectival
openers inflect for gender, so `encargado`/`encargada` and
`involucrado`/`involucrada` are each carried as a complete pair. The first-person
preterites (`ayudé`, `participé`, `trabajé`) do not inflect, and `responsable` is
epicene, so those need no pair.

`colaboré en` and `contribuí a` were removed alongside English `contributed to`,
for the same reason.
"""

_STRONG_VERB_EXAMPLES = ("Lideré", "Diseñé", "Implementé", "Reduje", "Optimicé")

# ── wl-007: first person ────────────────────────────────────────────

# Spanish is pro-drop: the subject lives in the conjugation, so `Lideré la
# migración` is correct CV style rather than a first-person flaw. Only the
# explicit pronoun counts.
#
# The clitic `me` is deliberately absent. `me encargué de` is both first-person
# and entirely idiomatic, and English's `me` ported straight across is the single
# false positive that would flag most well-formed Spanish bullets in a document.
_FIRST_PERSON = re.compile(r"\b(?:yo|mi|mis|mí)\b", re.IGNORECASE)

# ── wl-008: vague buzzwords ─────────────────────────────────────────

_BUZZWORDS = re.compile(
    r"\b(?:"
    r"proactiv[oa]|sinergias?|orientad[oa] a resultados|trabajo en equipo|"
    r"polivalente|dinámic[oa]|apasionad[oa]|motivad[oa]|"
    r"don de gentes|buena presencia"
    r")\b",
    re.IGNORECASE,
)

# ── wl-013: style consistency (Spanish-only implementation) ─────────

# A Spanish CV may legitimately use infinitive bullets ("Diseñar y mantener…"),
# first-person preterite ("Diseñé y mantuve…") or noun phrases. Mixing them
# within one role is the real flaw, so the rule compares styles rather than
# tenses. Present-vs-preterite is not separable from a noun phrase without a
# verb lexicon — `Desarrollo` is both — so only the two unambiguous styles are
# classified, and an entry mixing anything else is left alone.

INFINITIVE_ENDINGS = ("ar", "er", "ir")

# Words ending like an infinitive that are not one. Real infinitives are
# stressed on the final syllable and therefore never written with an accent, so
# the accent test in `linter` catches `líder` and `azúcar` on its own; this
# covers the unaccented remainder.
INFINITIVE_FALSE_POSITIVES = frozenset(
    {
        "lugar",
        "taller",
        "mujer",
        "ayer",
        "particular",
        "similar",
        "familiar",
        "auxiliar",
        "escolar",
        "hogar",
    }
)

# First-person preterite forms whose ending is not `-é` / `-í`. Listed rather
# than derived: the `-je` ending is shared with common nouns (`viaje`,
# `mensaje`, `equipaje`), so a suffix rule would classify those as verbs.
PRETERITE_IRREGULARS = frozenset(
    {
        # -uje / -je
        "dije",
        "reduje",
        "produje",
        "introduje",
        "traduje",
        "deduje",
        "conduje",
        "traje",
        "extraje",
        # -uve
        "tuve",
        "estuve",
        "obtuve",
        "mantuve",
        "sostuve",
        "detuve",
        "contuve",
        "anduve",
        # -use / -ude / -upe and the rest
        "puse",
        "propuse",
        "compuse",
        "expuse",
        "dispuse",
        "impuse",
        "pude",
        "supe",
        "quise",
        "hice",
        "vine",
        "fui",
        "di",
        "vi",
    }
)

# ── wl-015: metric and result framing ───────────────────────────────

# Spanish writes 50.000 rather than 50,000, reaches for € as often as $, and —
# unlike English — puts the currency symbol *after* the amount (`40.000 €`). The
# English pattern would miss the amount, the currency and their order.
_METRIC = re.compile(
    r"\d+\s*%"
    r"|\d+\s*x\b"
    r"|[€$]\s*[\d.,]+"
    r"|[\d.,]+\s*[€$]"
    r"|\d+\s*(?:k|mil|miles|millones|millón|M)\b",
    re.IGNORECASE,
)

# Gerunds and connectors that frame a result, plus the preterite result verbs a
# coordinated Spanish bullet uses instead ("…y reduje el tiempo un 60%").
_RESULT_FRAMING = re.compile(
    r"\b(?:"
    r"permitiendo|logrando|consiguiendo|generando|ahorrando|reduciendo|"
    r"aumentando|mejorando|acelerando|duplicando|escalando|eliminando|"
    r"gracias a|mediante|lo que|con lo que|que permitió|"
    r"reduje|redujo|redujimos|aumenté|aumentó|mejoré|mejoró|acorté|acortó|"
    r"ahorré|ahorró|generé|generó|dupliqué|duplicó|permitió|permitieron|"
    r"logré|logró|conseguí|consiguió|eliminé|eliminó"
    r")\b",
    re.IGNORECASE,
)

# ── wl-025: missing diacritics (Spanish-only rule) ──────────────────

# A closed list of high-frequency CV terms whose unaccented spelling is not a
# Spanish word, so a match is a typo rather than a judgement call. Ambiguous
# pairs are deliberately absent: `publico` is a valid verb form (`yo publico`),
# `ano` is a real word, and flagging either would cost more trust than the rule
# earns. This is the rule that makes the Spanish linter read as native rather
# than ported.
DIACRITIC_TERMS = {
    "gestion": "gestión",
    "analisis": "análisis",
    "implementacion": "implementación",
    "migracion": "migración",
    "optimizacion": "optimización",
    "automatizacion": "automatización",
    "integracion": "integración",
    "administracion": "administración",
    "aplicacion": "aplicación",
    "informacion": "información",
    "comunicacion": "comunicación",
    "formacion": "formación",
    "investigacion": "investigación",
    "planificacion": "planificación",
    "produccion": "producción",
    "programacion": "programación",
    "configuracion": "configuración",
    "validacion": "validación",
    "documentacion": "documentación",
    "colaboracion": "colaboración",
    "coordinacion": "coordinación",
    "evaluacion": "evaluación",
    "reduccion": "reducción",
    "creacion": "creación",
    "direccion": "dirección",
    "seleccion": "selección",
    "supervision": "supervisión",
    "version": "versión",
    "revision": "revisión",
    "precision": "precisión",
    "decision": "decisión",
    "division": "división",
    "tecnico": "técnico",
    "tecnica": "técnica",
    "informatica": "informática",
    "ingenieria": "ingeniería",
    "academico": "académico",
    "matematicas": "matemáticas",
    "estadistica": "estadística",
    "logistica": "logística",
    "practicas": "prácticas",
    "metodologia": "metodología",
    "tecnologia": "tecnología",
    "economia": "economía",
    "energia": "energía",
    "area": "área",
    "exito": "éxito",
    "diseno": "diseño",
    "espanol": "español",
    "compania": "compañía",
    "maquina": "máquina",
    "codigo": "código",
    "numero": "número",
    "parametro": "parámetro",
    "grafico": "gráfico",
    "historico": "histórico",
    "estrategico": "estratégico",
    "especifico": "específico",
    "automatico": "automático",
    "electronico": "electrónico",
    "basico": "básico",
    "rapido": "rápido",
    "ultimo": "último",
}

DIACRITIC_PATTERN = re.compile(
    r"\b(?:" + "|".join(sorted(DIACRITIC_TERMS)) + r")\b",
    re.IGNORECASE,
)

# ── match: stop words ───────────────────────────────────────────────

# Without these a Spanish job description returns `de / la / que / el` as its
# top keywords and the gap analysis is noise.
_JD_MARKERS = (
    "responsabilidades",
    "requisitos",
    "requerimientos",
    "cualificaciones",
    "qué harás",
    "lo que harás",
    "buscamos",
    "estamos buscando",
    "se ofrece",
    "se requiere",
    "el puesto",
    "sobre el puesto",
    "años de experiencia",
    "valorable",
    "beneficios",
    "postular",
    "postúlate",
    "igualdad de oportunidades",
)
"""Native phrasing, not a translation of the English list.

`se ofrece` / `se requiere` are the impersonal constructions Spanish postings are
built from and have no English counterpart here, and `postular` is the Latin
American verb where Spain would write `inscribirse`. Both are carried because the
locale is one language, not one country.
"""


_STOP_WORDS = frozenset(
    {
        "a",
        "al",
        "algo",
        "algunos",
        "ante",
        "antes",
        "aquel",
        "aquella",
        "aquello",
        "aqui",
        "aquí",
        "asi",
        "así",
        "aun",
        "aún",
        "bajo",
        "bien",
        "cada",
        "como",
        "cómo",
        "con",
        "contra",
        "cual",
        "cuál",
        "cuando",
        "cuándo",
        "de",
        "del",
        "desde",
        "donde",
        "dónde",
        "dos",
        "durante",
        "e",
        "el",
        "él",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "era",
        "eran",
        "eres",
        "es",
        "esa",
        "esas",
        "ese",
        "eso",
        "esos",
        "esta",
        "está",
        "están",
        "estas",
        "este",
        "esto",
        "estos",
        "fue",
        "fueron",
        "ha",
        "haber",
        "habia",
        "había",
        "han",
        "hasta",
        "hay",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "más",
        "me",
        "mi",
        "mis",
        "mucho",
        "muy",
        "nada",
        "ni",
        "no",
        "nos",
        "nosotros",
        "nuestra",
        "nuestro",
        "o",
        "os",
        "otra",
        "otras",
        "otro",
        "otros",
        "para",
        "pero",
        "poco",
        "por",
        "porque",
        "que",
        "qué",
        "quien",
        "quién",
        "se",
        "sea",
        "segun",
        "según",
        "ser",
        "si",
        "sí",
        "sido",
        "siempre",
        "sin",
        "sobre",
        "solo",
        "sólo",
        "son",
        "su",
        "sus",
        "tambien",
        "también",
        "tanto",
        "te",
        "tiene",
        "tienen",
        "todo",
        "todos",
        "tu",
        "tus",
        "un",
        "una",
        "uno",
        "unos",
        "y",
        "ya",
        "yo",
    }
)


LOCALE = LintLocale(
    code="es",
    passive_patterns=(_PASSIVE_PERIPHRASTIC, _PASSIVE_REFLEJA),
    passive_false_positives=_PASSIVE_FALSE_POSITIVES,
    noise_skills=_NOISE_SKILLS,
    weak_openers=_WEAK_OPENERS,
    strong_verb_examples=_STRONG_VERB_EXAMPLES,
    # Scaled from English by 1.22, the ratio measured from matched en/es renders
    # of the same CV through the same template.
    min_highlight_words=10,
    max_highlight_words=30,
    first_person_pattern=_FIRST_PERSON,
    buzzwords_pattern=_BUZZWORDS,
    # Skill *names* do not expand the way prose does, so these are unchanged.
    min_skills=8,
    max_skills=25,
    # Measured, not inferred, and it runs the opposite way to the assumption: a
    # Spanish page holds ~22% *more* words than an English one, because the
    # expansion shows up as more short function words rather than as more page.
    words_per_page=610,
    min_summary_words=24,
    max_summary_words=95,
    metric_pattern=_METRIC,
    result_framing_pattern=_RESULT_FRAMING,
    stop_words=_STOP_WORDS,
    jd_markers=_JD_MARKERS,
)
