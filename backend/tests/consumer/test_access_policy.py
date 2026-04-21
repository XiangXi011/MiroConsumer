from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.access_policy import resolve_visible_findings
from app.services.consumer.models import GraphVisibility, ResearchFinding


def test_round_zero_only_exposes_initial_knowledge():
    visible = resolve_visible_findings(
        persona={"search_propensity": "high", "cognition_level": "high"},
        findings=[
            ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Deep risk", visibility=GraphVisibility.Restricted)
        ],
        round_index=0,
    )
    assert visible == []


def test_high_search_persona_can_unlock_restricted_findings_after_round_one():
    visible = resolve_visible_findings(
        persona={"search_propensity": "high", "cognition_level": "high"},
        findings=[
            ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Deep risk", visibility=GraphVisibility.Restricted)
        ],
        round_index=2,
    )
    assert [item.finding_id for item in visible] == ["r1"]


def test_propagation_only_visible_to_all_after_round_one():
    visible = resolve_visible_findings(
        persona={"search_propensity": "low", "cognition_level": "medium"},
        findings=[
            ResearchFinding(finding_id="p1", finding_type="trend_signal", summary="Buzz", visibility=GraphVisibility.Propagation_Only)
        ],
        round_index=1,
    )
    assert [item.finding_id for item in visible] == ["p1"]


def test_low_search_persona_cannot_unlock_restricted_findings():
    visible = resolve_visible_findings(
        persona={"search_propensity": "low", "cognition_level": "medium"},
        findings=[
            ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Deep risk", visibility=GraphVisibility.Restricted)
        ],
        round_index=2,
    )
    assert visible == []
