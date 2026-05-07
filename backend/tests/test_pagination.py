"""Tests for pagination utility."""

import pytest

from app.utils.pagination import paginate_query


class TestPaginateQuery:
    """paginate_query 测试套件"""

    def test_basic_pagination(self):
        data = list(range(50))
        result = paginate_query(data, page=1, per_page=10)
        assert result["items"] == list(range(10))
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["per_page"] == 10
        assert result["pagination"]["total"] == 50
        assert result["pagination"]["pages"] == 5

    def test_second_page(self):
        data = list(range(50))
        result = paginate_query(data, page=2, per_page=10)
        assert result["items"] == list(range(10, 20))

    def test_last_page_partial(self):
        data = list(range(25))
        result = paginate_query(data, page=3, per_page=10)
        assert result["items"] == [20, 21, 22, 23, 24]
        assert result["pagination"]["pages"] == 3

    def test_page_clamped_to_minimum(self):
        data = [1, 2, 3]
        result = paginate_query(data, page=0, per_page=10)
        assert result["pagination"]["page"] == 1

    def test_per_page_clamped_to_minimum(self):
        data = [1, 2, 3]
        result = paginate_query(data, page=1, per_page=0)
        assert result["pagination"]["per_page"] == 1

    def test_per_page_capped_at_100(self):
        data = list(range(200))
        result = paginate_query(data, page=1, per_page=500)
        assert result["pagination"]["per_page"] == 100
        assert len(result["items"]) == 100

    def test_empty_list(self):
        result = paginate_query([], page=1, per_page=10)
        assert result["items"] == []
        assert result["pagination"]["total"] == 0
        assert result["pagination"]["pages"] == 0

    def test_single_page(self):
        data = [1, 2, 3]
        result = paginate_query(data, page=1, per_page=10)
        assert result["items"] == [1, 2, 3]
        assert result["pagination"]["pages"] == 1

    def test_page_beyond_total(self):
        data = list(range(10))
        result = paginate_query(data, page=100, per_page=10)
        assert result["items"] == []
        assert result["pagination"]["total"] == 10
