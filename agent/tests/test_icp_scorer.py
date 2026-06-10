"""ICP scorer: annotates everything, drops nothing, sort is decision support."""

from __future__ import annotations

import json
from typing import Any

import httpx
import respx

from azul.discovery.base import ProspectCandidate
from azul.discovery.icp_scorer import score_candidates, sorted_by_score
from tests.test_brief import writer_env
from tests.test_web_discovery import BRIEF

WRITER = "https://api.deepseek.com/v1"


def _llm(payload: dict[str, Any]) -> httpx.Response:
    content = json.dumps(payload, ensure_ascii=False)
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _three() -> list[ProspectCandidate]:
    return [
        ProspectCandidate(
            company_name="Pixel Agence", domain="pixel.fr",
            founder_name="Léa B", founder_role="fondatrice",
            raw_context="agence web e-commerce, 12 personnes, Paris, pas de DPO",
        ),
        ProspectCandidate(
            company_name="Studio Flou", domain="flou.io",
            raw_context="studio de design, taille inconnue",
        ),
        ProspectCandidate(
            company_name="AcierPro", domain="acierpro.com",
            raw_context="grossiste en métallurgie, 800 salariés, Allemagne",
        ),
    ]


def test_three_candidates_scored_ordered_none_dropped() -> None:
    scores = {
        "scores": [
            {"index": 0, "score": 0.95, "reason": "agence web FR e-commerce sans DPO — exact"},
            {"index": 1, "score": 0.5, "reason": "design proche du web, taille inconnue"},
            {"index": 2, "score": 0.05, "reason": "métallurgie DE, hors cible"},
        ]
    }
    candidates = _three()
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(return_value=_llm(scores))
        out = score_candidates(BRIEF, candidates)

    assert out is candidates and len(out) == 3  # NOTHING dropped, same list
    ranked = sorted_by_score(out)
    assert [c.domain for c in ranked] == ["pixel.fr", "flou.io", "acierpro.com"]
    assert all(c.score_reason for c in ranked)
    assert ranked[0].icp_score is not None and ranked[0].icp_score > 0.9
    assert ranked[-1].icp_score is not None and ranked[-1].icp_score < 0.1


def test_scoring_failure_keeps_and_annotates() -> None:
    candidates = _three()
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(500))
        out = score_candidates(BRIEF, candidates)
    assert len(out) == 3  # still nothing dropped
    assert all(c.icp_score is None for c in out)
    assert all(c.score_reason and "indisponible" in c.score_reason for c in out)
    # Unscored sink to the bottom but remain visible.
    assert len(sorted_by_score(out)) == 3


def test_scores_are_clamped_to_unit_interval() -> None:
    scores = {
        "scores": [
            {"index": 0, "score": 1.7, "reason": "trop enthousiaste"},
            {"index": 1, "score": -0.3, "reason": "trop négatif"},
            {"index": 2, "score": "n/a", "reason": "illisible"},
        ]
    }
    candidates = _three()
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(return_value=_llm(scores))
        score_candidates(BRIEF, candidates)
    assert candidates[0].icp_score == 1.0
    assert candidates[1].icp_score == 0.0
    assert candidates[2].icp_score is None  # junk score -> unscored, reason kept
    assert candidates[2].score_reason == "illisible"


def test_batching_over_ten_candidates() -> None:
    many = [
        ProspectCandidate(company_name=f"B{i}", domain=f"b{i}.fr", raw_context="ctx")
        for i in range(12)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        sent = json.loads(body["messages"][1]["content"].split("CANDIDATES: ", 1)[1])
        return _llm(
            {"scores": [{"index": c["index"], "score": 0.5, "reason": "ok"} for c in sent]}
        )

    with writer_env(), respx.mock(base_url=WRITER) as router:
        route = router.post("/chat/completions").mock(side_effect=handler)
        score_candidates(BRIEF, many)
    assert route.call_count == 2  # 10 + 2
    assert all(c.icp_score == 0.5 for c in many)
