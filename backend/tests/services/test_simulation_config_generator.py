"""Tests for simulation_config_generator core logic."""

from __future__ import annotations

import pytest
from dataclasses import asdict

from app.services.simulation_config_generator import (
    AgentActivityConfig,
    CHINA_TIMEZONE_CONFIG,
    EventConfig,
    PlatformConfig,
    SimulationConfigGenerator,
    SimulationParameters,
    TimeSimulationConfig,
)


class TestChinaTimezoneConfig:
    """Test CHINA_TIMEZONE_CONFIG constant."""

    def test_has_required_keys(self):
        """Config has all required time period keys."""
        assert "dead_hours" in CHINA_TIMEZONE_CONFIG
        assert "morning_hours" in CHINA_TIMEZONE_CONFIG
        assert "work_hours" in CHINA_TIMEZONE_CONFIG
        assert "peak_hours" in CHINA_TIMEZONE_CONFIG
        assert "night_hours" in CHINA_TIMEZONE_CONFIG
        assert "activity_multipliers" in CHINA_TIMEZONE_CONFIG

    def test_multiplier_ranges(self):
        """Activity multipliers are in reasonable ranges."""
        mults = CHINA_TIMEZONE_CONFIG["activity_multipliers"]
        assert 0 < mults["dead"] < 1
        assert 0 < mults["morning"] < 1
        assert 0 < mults["work"] < 2
        assert mults["peak"] >= 1
        assert 0 < mults["night"] < 1


class TestAgentActivityConfig:
    """Test AgentActivityConfig dataclass."""

    def test_creation(self):
        """Config can be created with required fields."""
        cfg = AgentActivityConfig(
            agent_id=0,
            entity_uuid="uuid-1",
            entity_name="Test Entity",
            entity_type="Person",
        )
        assert cfg.agent_id == 0
        assert cfg.entity_uuid == "uuid-1"
        assert cfg.entity_name == "Test Entity"
        assert cfg.entity_type == "Person"

    def test_defaults(self):
        """Config has sensible defaults."""
        cfg = AgentActivityConfig(
            agent_id=0,
            entity_uuid="u1",
            entity_name="E",
            entity_type="Person",
        )
        assert cfg.activity_level == 0.5
        assert cfg.posts_per_hour == 1.0
        assert cfg.comments_per_hour == 2.0
        assert cfg.sentiment_bias == 0.0
        assert cfg.stance == "neutral"
        assert cfg.influence_weight == 1.0

    def test_custom_values(self):
        """Config accepts custom values."""
        cfg = AgentActivityConfig(
            agent_id=1,
            entity_uuid="u2",
            entity_name="Media",
            entity_type="MediaOutlet",
            activity_level=0.8,
            posts_per_hour=5.0,
            sentiment_bias=-0.5,
            stance="opposing",
            influence_weight=2.5,
        )
        assert cfg.activity_level == 0.8
        assert cfg.posts_per_hour == 5.0
        assert cfg.sentiment_bias == -0.5
        assert cfg.stance == "opposing"
        assert cfg.influence_weight == 2.5


class TestTimeSimulationConfig:
    """Test TimeSimulationConfig dataclass."""

    def test_defaults(self):
        """Config has sensible defaults."""
        cfg = TimeSimulationConfig()
        assert cfg.total_simulation_hours == 72
        assert cfg.minutes_per_round == 60
        assert cfg.agents_per_hour_min == 5
        assert cfg.agents_per_hour_max == 20
        assert cfg.peak_activity_multiplier == 1.5
        assert cfg.off_peak_activity_multiplier == 0.05
        assert cfg.morning_activity_multiplier == 0.4
        assert cfg.work_activity_multiplier == 0.7

    def test_custom_values(self):
        """Config accepts custom values."""
        cfg = TimeSimulationConfig(
            total_simulation_hours=48,
            minutes_per_round=30,
            agents_per_hour_min=3,
            agents_per_hour_max=15,
        )
        assert cfg.total_simulation_hours == 48
        assert cfg.minutes_per_round == 30
        assert cfg.agents_per_hour_min == 3
        assert cfg.agents_per_hour_max == 15


class TestEventConfig:
    """Test EventConfig dataclass."""

    def test_defaults(self):
        """Config has empty defaults."""
        cfg = EventConfig()
        assert cfg.initial_posts == []
        assert cfg.scheduled_events == []
        assert cfg.hot_topics == []
        assert cfg.narrative_direction == ""

    def test_with_events(self):
        """Config can hold events."""
        cfg = EventConfig(
            initial_posts=[{"content": "Hello", "poster_type": "Person"}],
            hot_topics=["topic1", "topic2"],
            narrative_direction="positive",
        )
        assert len(cfg.initial_posts) == 1
        assert cfg.hot_topics == ["topic1", "topic2"]
        assert cfg.narrative_direction == "positive"


class TestPlatformConfig:
    """Test PlatformConfig dataclass."""

    def test_twitter_defaults(self):
        """Twitter config has expected defaults."""
        cfg = PlatformConfig(platform="twitter")
        assert cfg.platform == "twitter"
        assert cfg.recency_weight == 0.4
        assert cfg.popularity_weight == 0.3
        assert cfg.relevance_weight == 0.3
        assert cfg.viral_threshold == 10
        assert cfg.echo_chamber_strength == 0.5

    def test_reddit_defaults(self):
        """Reddit config has expected defaults."""
        cfg = PlatformConfig(platform="reddit")
        assert cfg.platform == "reddit"
        assert cfg.viral_threshold == 10

    def test_custom_values(self):
        """Config accepts custom values."""
        cfg = PlatformConfig(
            platform="twitter",
            recency_weight=0.6,
            viral_threshold=20,
            echo_chamber_strength=0.8,
        )
        assert cfg.recency_weight == 0.6
        assert cfg.viral_threshold == 20
        assert cfg.echo_chamber_strength == 0.8


class TestSimulationParameters:
    """Test SimulationParameters dataclass."""

    def test_creation(self):
        """Parameters can be created with required fields."""
        params = SimulationParameters(
            simulation_id="sim_1",
            project_id="proj_1",
            graph_id="graph_1",
            simulation_requirement="Test requirement",
        )
        assert params.simulation_id == "sim_1"
        assert params.project_id == "proj_1"

    def test_to_dict_basic(self):
        """Parameters serialize to dict."""
        params = SimulationParameters(
            simulation_id="sim_1",
            project_id="proj_1",
            graph_id="g1",
            simulation_requirement="req",
        )
        d = params.to_dict()
        assert d["simulation_id"] == "sim_1"
        assert d["project_id"] == "proj_1"
        assert d["graph_id"] == "g1"
        assert d["simulation_requirement"] == "req"
        assert d["llm_model"] == ""
        assert d["llm_base_url"] == ""

    def test_to_dict_with_platforms(self):
        """Parameters with platforms serialize correctly."""
        params = SimulationParameters(
            simulation_id="sim_1",
            project_id="proj_1",
            graph_id="g1",
            simulation_requirement="req",
            twitter_config=PlatformConfig(platform="twitter"),
            reddit_config=PlatformConfig(platform="reddit"),
        )
        d = params.to_dict()
        assert d["twitter_config"] is not None
        assert d["twitter_config"]["platform"] == "twitter"
        assert d["reddit_config"] is not None
        assert d["reddit_config"]["platform"] == "reddit"

    def test_to_json(self):
        """Parameters serialize to JSON string."""
        params = SimulationParameters(
            simulation_id="sim_1",
            project_id="proj_1",
            graph_id="g1",
            simulation_requirement="req",
        )
        json_str = params.to_json()
        assert "sim_1" in json_str
        assert "proj_1" in json_str

    def test_default_time_config(self):
        """Parameters has default TimeSimulationConfig."""
        params = SimulationParameters(
            simulation_id="s1",
            project_id="p1",
            graph_id="g1",
            simulation_requirement="req",
        )
        assert params.time_config is not None
        assert params.time_config.total_simulation_hours == 72

    def test_default_event_config(self):
        """Parameters has default EventConfig."""
        params = SimulationParameters(
            simulation_id="s1",
            project_id="p1",
            graph_id="g1",
            simulation_requirement="req",
        )
        assert params.event_config is not None
        assert params.event_config.initial_posts == []


class TestSimulationConfigGeneratorInit:
    """Test SimulationConfigGenerator initialization."""

    def test_requires_api_key(self, monkeypatch):
        """Generator requires API key."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", None
        )
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            SimulationConfigGenerator()

    def test_init_with_explicit_key(self):
        """Generator can be initialized with explicit API key."""
        # When a valid api_key is provided, should succeed even if Config.LLM_API_KEY is None
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", None
        )
        # Without api_key param, should raise
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            SimulationConfigGenerator()
        # With explicit api_key, should succeed
        gen = SimulationConfigGenerator(api_key="test_key")
        assert gen.api_key == "test_key"
        monkeypatch.undo()

    def test_class_constants(self):
        """Generator has expected class constants."""
        assert SimulationConfigGenerator.MAX_CONTEXT_LENGTH > 0
        assert SimulationConfigGenerator.AGENTS_PER_BATCH > 0
        assert SimulationConfigGenerator.TIME_CONFIG_CONTEXT_LENGTH > 0
        assert SimulationConfigGenerator.EVENT_CONFIG_CONTEXT_LENGTH > 0
        assert SimulationConfigGenerator.ENTITY_SUMMARY_LENGTH > 0
        assert SimulationConfigGenerator.ENTITIES_PER_TYPE_DISPLAY > 0


class TestSimulationConfigGeneratorHelpers:
    """Test SimulationConfigGenerator helper methods."""

    def test_fix_truncated_json_braces(self, monkeypatch):
        """_fix_truncated_json handles unclosed braces."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")
        fixed = gen._fix_truncated_json('{"key": "value"')
        assert "}" in fixed

    def test_fix_truncated_json_brackets(self, monkeypatch):
        """_fix_truncated_json handles unclosed brackets."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")
        fixed = gen._fix_truncated_json('[1, 2')
        assert "]" in fixed

    def test_fix_truncated_json_already_valid(self, monkeypatch):
        """_fix_truncated_json preserves valid JSON."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")
        valid = '{"key": "value"}'
        fixed = gen._fix_truncated_json(valid)
        assert fixed == valid

    def test_get_default_time_config(self, monkeypatch):
        """Default time config is returned."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")
        config = gen._get_default_time_config(10)
        assert "total_simulation_hours" in config
        assert "minutes_per_round" in config
        assert "peak_hours" in config
        assert "reasoning" in config

    def test_parse_time_config(self, monkeypatch):
        """Time config parsing creates valid object."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")
        result = {
            "total_simulation_hours": 48,
            "minutes_per_round": 30,
            "agents_per_hour_min": 3,
            "agents_per_hour_max": 10,
            "peak_hours": [20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        }
        config = gen._parse_time_config(result, 20)
        assert config.total_simulation_hours == 48
        assert config.minutes_per_round == 30
        assert config.peak_hours == [20, 21, 22]

    def test_parse_time_config_clamps_max(self, monkeypatch):
        """Time config parsing clamps values exceeding entity count."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")
        result = {
            "agents_per_hour_min": 100,
            "agents_per_hour_max": 200,
        }
        config = gen._parse_time_config(result, 10)
        assert config.agents_per_hour_min <= 10
        assert config.agents_per_hour_max <= 10
        assert config.agents_per_hour_min < config.agents_per_hour_max

    def test_parse_event_config(self, monkeypatch):
        """Event config parsing creates valid object."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")
        result = {
            "hot_topics": ["topic1"],
            "narrative_direction": "positive",
            "initial_posts": [{"content": "Hello", "poster_type": "Person"}],
        }
        config = gen._parse_event_config(result)
        assert config.hot_topics == ["topic1"]
        assert config.narrative_direction == "positive"
        assert len(config.initial_posts) == 1

    def test_generate_agent_config_by_rule_official(self, monkeypatch):
        """Rule-based config for official entity type."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")

        from unittest.mock import MagicMock

        entity = MagicMock()
        entity.get_entity_type.return_value = "University"
        entity.name = "Test University"
        cfg = gen._generate_agent_config_by_rule(entity)
        assert cfg["activity_level"] < 0.5
        assert cfg["influence_weight"] > 2.0

    def test_generate_agent_config_by_rule_media(self, monkeypatch):
        """Rule-based config for media entity type."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")

        from unittest.mock import MagicMock

        entity = MagicMock()
        entity.get_entity_type.return_value = "MediaOutlet"
        entity.name = "News Corp"
        cfg = gen._generate_agent_config_by_rule(entity)
        assert cfg["influence_weight"] > 2.0

    def test_generate_agent_config_by_rule_student(self, monkeypatch):
        """Rule-based config for student entity type."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")

        from unittest.mock import MagicMock

        entity = MagicMock()
        entity.get_entity_type.return_value = "Student"
        entity.name = "Student A"
        cfg = gen._generate_agent_config_by_rule(entity)
        assert cfg["activity_level"] > 0.5
        assert cfg["influence_weight"] < 1.0

    def test_generate_agent_config_by_rule_default(self, monkeypatch):
        """Rule-based config for unknown entity type."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")

        from unittest.mock import MagicMock

        entity = MagicMock()
        entity.get_entity_type.return_value = "Unknown"
        entity.name = "Unknown Entity"
        cfg = gen._generate_agent_config_by_rule(entity)
        assert "activity_level" in cfg
        assert "stance" in cfg
        assert "influence_weight" in cfg


class TestSimulationConfigGeneratorAssignPosts:
    """Test SimulationConfigGenerator post assignment."""

    def test_assign_initial_post_agents_empty(self, monkeypatch):
        """Assigning with no posts returns config unchanged."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")
        event_config = EventConfig(initial_posts=[])
        result = gen._assign_initial_post_agents(event_config, [])
        assert result.initial_posts == []

    def test_assign_initial_post_agents_fallback(self, monkeypatch):
        """Assigning falls back to highest influence agent."""
        monkeypatch.setattr(
            "app.services.simulation_config_generator.Config.LLM_API_KEY", "test"
        )
        gen = SimulationConfigGenerator(api_key="test")

        agent1 = AgentActivityConfig(
            agent_id=0,
            entity_uuid="u1",
            entity_name="Low",
            entity_type="Person",
            influence_weight=1.0,
        )
        agent2 = AgentActivityConfig(
            agent_id=1,
            entity_uuid="u2",
            entity_name="High",
            entity_type="Person",
            influence_weight=3.0,
        )
        event_config = EventConfig(
            initial_posts=[{"content": "Post", "poster_type": "NonExistent"}]
        )
        result = gen._assign_initial_post_agents(event_config, [agent1, agent2])
        assert len(result.initial_posts) == 1
        assert result.initial_posts[0]["poster_agent_id"] == 1  # highest influence
