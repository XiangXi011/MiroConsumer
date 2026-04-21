from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.brief_adapter import ConsumerBriefAdapter
from app.services.consumer.models import GraphVisibility, ResearchFinding
from app.services.consumer.research_ingest import (
    build_research_findings,
    build_research_summary,
    resolve_research_findings,
)


def test_research_ingest_builds_typed_findings():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["High-protein yogurt pouch"],
            "copy_material": ["14g protein", "low sugar"],
            "research_goal": "Find likely debate points",
            "optional_background_materials": ["Ingredient concern: sweetener debates"],
        }
    )

    findings = build_research_findings(brief)

    assert findings[0].finding_type in {"category_context", "risk_signal", "trend_signal"}
    assert findings[0].visibility in {GraphVisibility.Propagation_Only, GraphVisibility.Restricted}
    assert findings[0].summary


def test_auto_enrich_uses_provider_output_without_manual_background():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["High-protein yogurt pouch"],
            "copy_material": ["14g protein", "low sugar"],
            "research_goal": "Find likely debate points",
            "research_mode": "auto_enrich",
        }
    )

    findings = resolve_research_findings(
        brief,
        provider=lambda _: [
            ResearchFinding(
                finding_id="auto_1",
                finding_type="trend_signal",
                summary="High-protein breakfast is trending",
                visibility=GraphVisibility.Propagation_Only,
            )
        ],
    )

    assert [item.finding_id for item in findings] == ["auto_1"]


def test_research_ingest_can_build_pinned_research_summary():
    findings = [ResearchFinding(finding_id="r1", finding_type="risk_signal", summary="Sweetener concern", visibility=GraphVisibility.Restricted)]
    summary = build_research_summary(findings)
    assert "Sweetener concern" in summary
