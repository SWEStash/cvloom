"""CVs to run the AI features against, including the ones that go wrong.

The rest of the AI tests feed the orchestrators a hand-written JSON string and
check it parses. That proves the plumbing and nothing about the output, so this
module exists to give the evaluation suite something to be wrong *about*.

Two sources, deliberately mixed. `examples/` and `examples-es/` are the repo's own
demo projects, resolved through the same path a user's project takes — they are
the only fixtures that prove the real pipeline end to end. Everything else is
synthetic and built to fail one way each: a CV with no metrics anywhere, one that
is four pages, one with an empty `work` section, a job description that is not a
job description. A model that looks competent on a good CV and confabulates on an
empty one has failed at the case where the harm is real.

Fixtures are Python rather than a directory of YAML because they are inputs to
assertions, not documents anyone reads. `examples-es/` is loaded rather than
extended, and the deliberately-bad Spanish case lives here instead: that project
produces exactly one lint finding, so it proves locale handling and barely
exercises the analysis block, and growing it to fix that would make the demo CV
worse for the people it is actually a demo for.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cvloom import builder
from cvloom.models import ResolvedProfile
from tests.conftest import make_resolved

_REPO = Path(__file__).parent.parent

REAL_JD = (_REPO / "examples" / "stripe-infra-jd.txt").read_text()

NOT_A_JD = """
Privacy Policy — last updated March 2024

We collect information you provide directly to us, including when you create an
account, fill out a form, or communicate with us. We use cookies and similar
tracking technologies to collect information about your browsing activities.
You may opt out of certain collection by adjusting your browser settings.
"""


@dataclass(frozen=True)
class Case:
    """One CV, and what it is meant to expose."""

    name: str
    resolved: ResolvedProfile
    jd: str | None = None
    expects_empty: bool = False
    """Whether an honest answer is "there is nothing here to assess".

    Set on the inputs where the correct response is a refusal to analyse rather
    than an analysis — which is the behaviour a confident model is worst at, and
    the reason these are graded separately from the rest.
    """


def _work(company: str, *highlights: str) -> dict[str, object]:
    return {
        "company": company,
        "title": "Senior Engineer",
        "start_date": "2020-01",
        "end_date": "Present",
        "highlights": list(highlights),
    }


def _resolved(work: list[dict[str, object]], **kwargs: object) -> ResolvedProfile:
    return make_resolved(
        work=work,
        skills=[{"category": "Languages", "items": ["Python", "Go", "SQL"]}],
        show={"work": True, "skills": True},
        section_order=["work", "skills"],
        **kwargs,  # type: ignore[arg-type]
    )


def _project(name: str) -> ResolvedProfile:
    return builder.resolve_project(_REPO / name, profile_name="general", public=True)


def cases() -> list[Case]:
    """The corpus, rebuilt per call so no test can mutate another's fixture."""
    return [
        Case("examples", _project("examples"), jd=REAL_JD),
        Case("examples-es", _project("examples-es")),
        Case(
            "no-metrics",
            _resolved(
                [
                    _work(
                        "Acme Corp",
                        "Built the deployment pipeline for the platform team.",
                        "Improved the reliability of the billing service.",
                        "Reduced the time it takes to onboard a new service.",
                    )
                ]
            ),
            jd=REAL_JD,
        ),
        Case(
            "weak-openers",
            _resolved(
                [
                    _work(
                        "Acme Corp",
                        "Helped the team ship the new billing service on schedule.",
                        "Was responsible for the deployment pipeline and its upkeep.",
                        "Participated in the migration from the monolith to services.",
                    )
                ]
            ),
        ),
        Case(
            "passive-throughout",
            _resolved(
                [
                    _work(
                        "Acme Corp",
                        "The deployment pipeline was rebuilt to cut release time by 40%.",
                        "Twelve services were migrated off the monolith over two quarters.",
                        "The billing system was maintained and its error rate was halved.",
                    )
                ]
            ),
        ),
        Case(
            "four-pages",
            _resolved(
                [
                    _work(
                        f"Company {n}",
                        *[
                            f"Delivered subsystem {n}.{i} and cut its latency by {i * 3}% "
                            "across the fleet, working with the platform team throughout."
                            for i in range(1, 9)
                        ],
                    )
                    for n in range(1, 9)
                ]
            ),
        ),
        Case(
            "one-line",
            # No summary and no skills, unlike the other synthetic cases. With
            # them the CV is thin but assessable, a model that assesses the
            # skills section is right to, and "report this as unusable" stops
            # being the correct answer — which makes it a fixture that grades
            # the wrong thing rather than a hard case.
            make_resolved(
                basics={"name": "Test", "label": "Engineer", "summary": ""},
                work=[_work("Acme Corp", "Wrote software.")],
                show={"work": True},
                section_order=["work"],
            ),
            expects_empty=True,
        ),
        Case(
            "empty-cv",
            make_resolved(
                basics={"name": "Test", "label": "", "summary": ""},
                show={"work": True},
                section_order=["work"],
            ),
            expects_empty=True,
        ),
        Case(
            "jd-is-a-privacy-policy",
            _project("examples"),
            jd=NOT_A_JD,
            expects_empty=True,
        ),
        Case(
            "spanish-no-metrics",
            make_resolved(
                work=[
                    {
                        "company": "Globex",
                        "title": "Ingeniera de Software",
                        "start_date": "2020-01",
                        "end_date": "Present",
                        "highlights": [
                            "Ayudé a migrar el monolito a una arquitectura de servicios.",
                            "Encargada de mantener el sistema de facturación del equipo.",
                            "Se implementó un nuevo proceso de despliegue para la plataforma.",
                        ],
                    }
                ],
                skills=[{"category": "Lenguajes", "items": ["Python", "Go", "SQL"]}],
                show={"work": True, "skills": True},
                section_order=["work", "skills"],
                locale_pack=_project("examples-es").locale,
            ),
        ),
        Case(
            "academic",
            make_resolved(
                work=[_work("University Lab", "Led the distributed systems reading group.")],
                publications=[
                    {
                        "name": "Consensus under partial synchrony",
                        "publisher": "SOSP",
                        "release_date": "2022-10",
                    }
                ],
                awards=[
                    {"title": "Best Paper", "awarder": "SOSP", "date": "2022-10"},
                ],
                skills=[{"category": "Languages", "items": ["Python", "Rust"]}],
                show={"work": True, "publications": True, "awards": True, "skills": True},
                section_order=["work", "publications", "awards", "skills"],
            ),
        ),
    ]
