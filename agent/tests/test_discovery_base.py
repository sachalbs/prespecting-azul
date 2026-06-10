"""CandidateDiscovery interface: candidate shape + pipeline-row compatibility."""

from __future__ import annotations

from typing import ClassVar

from azul.discovery.base import CandidateDiscovery, ProspectCandidate
from azul.discovery.brief import ICPBrief

BRIEF = ICPBrief(
    sells="audit RGPD",
    sector="agences web",
    company_size="5-30",
    geo="FR",
    target_role="fondateur",
    good_prospect="agence e-commerce sans DPO",
    pain_signals=("cookies",),
    tone="direct",
    raw_text="je vends un audit RGPD",
)


class FixedDiscovery(CandidateDiscovery):
    name: ClassVar[str] = "fixed"

    def discover(self, brief: ICPBrief, n: int) -> list[ProspectCandidate]:
        return [
            ProspectCandidate(
                company_name=f"Agence {i}",
                domain=f"agence{i}.fr",
                founder_name=f"Fondateur {i}",
                founder_role="CEO",
                source_url="https://annuaire.example/agences",
                raw_context=f"Agence {i} — growth, Paris, 12 personnes",
            )
            for i in range(1, n + 1)
        ]


def test_interface_returns_candidates_with_provenance() -> None:
    out = FixedDiscovery().discover(BRIEF, 3)
    assert len(out) == 3
    c = out[0]
    assert c.company_name and c.domain and c.source_url
    assert "growth" in c.raw_context  # the evidence travels with the candidate
    assert c.icp_score is None and c.score_reason is None  # annotated later, not here


def test_candidate_as_row_matches_the_csv_pipeline_shape() -> None:
    row = FixedDiscovery().discover(BRIEF, 1)[0].as_row()
    assert set(row) == {"full_name", "company", "company_domain", "title", "source_url"}
    assert row["company_domain"] == "agence1.fr"
    assert row["full_name"] == "Fondateur 1"
