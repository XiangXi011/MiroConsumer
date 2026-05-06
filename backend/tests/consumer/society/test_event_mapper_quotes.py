from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.event_mapper import ConsumerSocietyEventMapper
from app.services.consumer.society.population_models import ConsumerSocietyAgent


def _agent(agent_id, role, traits, price, evidence):
    return ConsumerSocietyAgent(
        agent_id=agent_id,
        parent_persona_id=agent_id,
        layer="core",
        segment=traits["name"],
        role=role,
        traits=traits,
        price_sensitivity=price,
        evidence_sensitivity=evidence,
    )


def test_event_mapper_generates_distinct_chinese_quotes_for_same_claim():
    mapper = ConsumerSocietyEventMapper()
    claim = "316不锈钢"
    agents = [
        _agent(
            "price",
            ConsumerRole.PriceSensitive,
            {
                "name": "价格比较型宝妈",
                "city_tier": "二线",
                "family_structure": "两代同住",
                "risk_sensitivities": ["价格虚高"],
                "expression_style": "直接比较",
            },
            0.9,
            0.4,
        ),
        _agent(
            "evidence",
            ConsumerRole.Skeptic,
            {
                "name": "成分证据型家庭主理人",
                "city_tier": "一线/新一线",
                "family_structure": "有孩子",
                "risk_sensitivities": ["材质安全"],
                "expression_style": "重视证据",
            },
            0.3,
            0.9,
        ),
        _agent(
            "family",
            ConsumerRole.TrustRepairable,
            {
                "name": "一线城市精致妈妈",
                "city_tier": "一线/新一线",
                "family_structure": "有1个3-8岁孩子",
                "risk_sensitivities": ["孩子是否愿意用"],
                "expression_style": "谨慎但愿意尝新",
            },
            0.4,
            0.8,
        ),
        _agent(
            "impulse",
            ConsumerRole.Amplifier,
            {
                "name": "直播尝鲜型年轻家庭",
                "city_tier": "新一线",
                "family_structure": "年轻小家庭",
                "risk_sensitivities": ["营销夸大"],
                "expression_style": "冲动尝鲜",
            },
            0.5,
            0.5,
        ),
    ]

    quotes = [
        mapper.map_agent_event(
            agent=agent,
            round_index=1,
            visible_claims=[claim],
            previous_events=[],
            brief_context={"claims": [claim]},
            research_findings=[],
        )["quote"]
        for agent in agents
    ]

    assert len(set(quotes)) == 4
    assert any("贵" in quote or "价格" in quote for quote in quotes)
    assert any("证明" in quote or "检测" in quote or "证据" in quote for quote in quotes)
    assert any("孩子" in quote or "家里" in quote for quote in quotes)
    assert any("直播" in quote or "想试" in quote or "种草" in quote for quote in quotes)
    assert all("claim" not in quote for quote in quotes)
    assert all("鎴" not in quote for quote in quotes)
