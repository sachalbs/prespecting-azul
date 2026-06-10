"""End-to-end discovery with mocks: brief -> web -> scoring -> selection -> Prospects.

Every external call (DeepSeek + Tavily) is mocked; the DB is real (test sqlite).
This is the exact flow `azul discover` drives.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import respx
from sqlalchemy import select

from azul.db.models import Campaign, DiscoveryCandidate, Prospect
from azul.db.session import session_scope
from azul.discovery.brief import BriefSession, save_brief
from azul.discovery.dedup import dedupe
from azul.discovery.icp_scorer import score_candidates
from azul.discovery.store import promote, ranked, render_table, save_candidates
from azul.discovery.web_discovery import WebDiscovery
from azul.enums import CampaignStatus
from azul.orchestrator.campaign import ensure_tenant
from tests.test_web_discovery import writer_env

WRITER = "https://api.deepseek.com/v1"
TAVILY = "https://api.tavily.com"


def _llm(payload: dict[str, Any]) -> httpx.Response:
    content = json.dumps(payload, ensure_ascii=False)
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


# One scripted DeepSeek conversation + discovery + scoring, in call order:
_LLM_SCRIPT = [
    # brief: one clarifying question, then done
    _llm({"done": False, "question": "Quelle géographie vises-tu ?"}),
    _llm(
        {
            "done": True,
            "brief": {
                "sells": "audit RGPD automatisé",
                "sector": "agences web",
                "company_size": "5-30",
                "geo": "France",
                "target_role": "fondateur",
                "good_prospect": "agence e-commerce sans DPO",
                "pain_signals": ["bannière cookies absente"],
                "tone": "direct",
            },
        }
    ),
    # discovery: query generation
    _llm({"queries": ["annuaire agences web france"]}),
    # discovery: mine the search snippets
    _llm(
        {
            "candidates": [
                {"company_name": "Pixel Agence", "domain": "pixel.fr",
                 "founder_name": "Léa Bois", "founder_role": "fondatrice"},
                {"company_name": "Webizi", "domain": "webizi.fr",
                 "founder_name": "Marc Hugo", "founder_role": "CEO"},
                {"company_name": "Déjà Connu", "domain": "deja.fr",
                 "founder_name": "", "founder_role": ""},
            ]
        }
    ),
    # discovery: mine the extracted page
    _llm(
        {
            "candidates": [
                {"company_name": "Grosse Industrie", "domain": "grosse-industrie.com",
                 "founder_name": "", "founder_role": ""},
            ]
        }
    ),
    # scoring (one batch)
    _llm(
        {
            "scores": [
                {"index": 0, "score": 0.92, "reason": "agence web FR, taille parfaite"},
                {"index": 1, "score": 0.61, "reason": "agence web, e-commerce à confirmer"},
                {"index": 2, "score": 0.1, "reason": "industrie lourde, hors cible"},
            ]
        }
    ),
]

_SEARCH = {
    "results": [
        {"url": "https://annuaire.example/agences", "content": "des agences...", "score": 0.8}
    ]
}
_EXTRACT = {
    "results": [
        {"url": "https://annuaire.example/agences", "raw_content": "la liste complète..."}
    ]
}


def test_full_discovery_flow_brief_to_prospects() -> None:
    with session_scope() as s:
        tenant = ensure_tenant(s, "e2e")
        # deja.fr was contacted before -> dedup must drop it silently
        s.add(Prospect(tenant_id=tenant.id, email="x@deja.fr", company_domain="deja.fr"))
        tid = tenant.id

    with writer_env(), respx.mock(assert_all_called=False) as router:
        router.post(f"{WRITER}/chat/completions").mock(side_effect=_LLM_SCRIPT)
        router.post(f"{TAVILY}/search").mock(return_value=httpx.Response(200, json=_SEARCH))
        router.post(f"{TAVILY}/extract").mock(return_value=httpx.Response(200, json=_EXTRACT))

        # 1. Conversational brief (one question, one answer).
        bs = BriefSession()
        q = bs.start("je vends un audit RGPD automatisé pour les agences web")
        assert q is not None and bs.reply("la France uniquement") is None
        brief = bs.brief
        assert brief is not None and brief.geo == "France"

        # 2. Discover -> dedup -> score -> persist (all annotated, none dropped).
        found = WebDiscovery().discover(brief, n=3)
        with session_scope() as s:
            brief_id = save_brief(s, tid, brief).id
            kept = dedupe(s, tid, found)
            assert {c.domain for c in kept} == {"pixel.fr", "webizi.fr", "grosse-industrie.com"}
            score_candidates(brief, kept)
            rows = save_candidates(s, tid, kept, brief_id=brief_id)
            table = render_table(rows)
            ordered = ranked(rows)
            # 3. The human keeps the top 2; the off-target one stays, annotated.
            prospects, campaign = promote(s, tid, ordered[:2], campaign_name="e2e run")
            assert len(prospects) == 2
            cid = campaign.id

    assert "pixel.fr" in table.splitlines()[2]  # best score renders first

    with session_scope() as s:
        promoted = s.scalars(
            select(Prospect).where(Prospect.tenant_id == tid, Prospect.source == "discovery")
        ).all()
        assert {p.company_domain for p in promoted} == {"pixel.fr", "webizi.fr"}
        pixel = next(p for p in promoted if p.company_domain == "pixel.fr")
        assert pixel.full_name == "Léa Bois"
        assert pixel.signals["icp_score"] == 0.92
        assert pixel.email == "lea.bois@pixel.fr"  # placeholder; pipeline verifies/replaces

        leftovers = s.scalars(
            select(DiscoveryCandidate).where(DiscoveryCandidate.promoted.is_(False))
        ).all()
        assert [r.domain for r in leftovers] == ["grosse-industrie.com"]
        assert leftovers[0].score_reason == "industrie lourde, hors cible"

        campaign_db = s.get(Campaign, cid)
        assert campaign_db is not None
        assert campaign_db.status == CampaignStatus.DISCOVERED
        assert len(list(campaign_db.leads)) == 2  # ready for azul approve-list
