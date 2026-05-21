"""Tests for graph_builder core logic."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.services.graph_builder import GraphInfo


class TestGraphInfo:
    """Test GraphInfo dataclass."""

    def test_basic_creation(self):
        """GraphInfo can be created with required fields."""
        info = GraphInfo(
            graph_id="g_123",
            node_count=10,
            edge_count=5,
            entity_types=["Person", "Organization"],
        )
        assert info.graph_id == "g_123"
        assert info.node_count == 10
        assert info.edge_count == 5
        assert info.entity_types == ["Person", "Organization"]

    def test_to_dict(self):
        """GraphInfo serializes to dict correctly."""
        info = GraphInfo(
            graph_id="g_test",
            node_count=100,
            edge_count=50,
            entity_types=["Person", "Organization", "Location"],
        )
        d = info.to_dict()
        assert d["graph_id"] == "g_test"
        assert d["node_count"] == 100
        assert d["edge_count"] == 50
        assert d["entity_types"] == ["Person", "Organization", "Location"]

    def test_empty_entity_types(self):
        """GraphInfo with empty entity types is valid."""
        info = GraphInfo(
            graph_id="g_empty",
            node_count=0,
            edge_count=0,
            entity_types=[],
        )
        d = info.to_dict()
        assert d["node_count"] == 0
        assert d["edge_count"] == 0
        assert d["entity_types"] == []

    def test_zero_nodes(self):
        """GraphInfo with zero nodes is valid."""
        info = GraphInfo(
            graph_id="g_zero",
            node_count=0,
            edge_count=0,
            entity_types=[],
        )
        assert info.node_count == 0

    def test_round_trip(self):
        """GraphInfo survives to_dict round-trip."""
        info = GraphInfo(
            graph_id="g_round",
            node_count=42,
            edge_count=21,
            entity_types=["TypeA"],
        )
        d = info.to_dict()
        info2 = GraphInfo(**d)
        assert info2.graph_id == info.graph_id
        assert info2.node_count == info.node_count
        assert info2.edge_count == info.edge_count
        assert info2.entity_types == info.entity_types
