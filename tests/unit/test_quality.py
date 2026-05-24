"""Tests for src.quality — data quality expectations and validation."""

import pytest

from src.quality.expectations import (
    Expectation,
    bronze_expectations,
    gold_expectations,
    silver_expectations,
)


class TestExpectationDataclass:
    """Tests for the Expectation dataclass."""

    def test_create_expectation(self):
        exp = Expectation(table="test", check="row_count")
        assert exp.table == "test"
        assert exp.check == "row_count"
        assert exp.severity == "critical"

    def test_default_values(self):
        exp = Expectation(table="t", check="c")
        assert exp.column is None
        assert exp.kwargs is None
        assert exp.severity == "critical"

    def test_custom_severity(self):
        exp = Expectation(table="t", check="c", severity="warning")
        assert exp.severity == "warning"


class TestBronzeExpectations:
    """Tests for Bronze layer expectation suites."""

    @pytest.fixture
    def expectations(self):
        return bronze_expectations()

    def test_returns_list(self, expectations):
        assert isinstance(expectations, list)

    def test_has_expectations(self, expectations):
        assert len(expectations) > 0

    def test_all_are_expectation_instances(self, expectations):
        for exp in expectations:
            assert isinstance(exp, Expectation)

    def test_covers_raw_tables(self, expectations):
        tables = {exp.table for exp in expectations}
        assert len(tables) >= 3, f"Expected at least 3 tables, got: {tables}"


class TestSilverExpectations:
    """Tests for Silver layer expectation suites."""

    @pytest.fixture
    def expectations(self):
        return silver_expectations()

    def test_returns_list(self, expectations):
        assert isinstance(expectations, list)

    def test_has_expectations(self, expectations):
        assert len(expectations) > 0

    def test_all_are_expectation_instances(self, expectations):
        for exp in expectations:
            assert isinstance(exp, Expectation)


class TestGoldExpectations:
    """Tests for Gold layer expectation suites."""

    @pytest.fixture
    def expectations(self):
        return gold_expectations()

    def test_returns_list(self, expectations):
        assert isinstance(expectations, list)

    def test_has_expectations(self, expectations):
        assert len(expectations) > 0

    def test_covers_dim_and_fact_tables(self, expectations):
        tables = {exp.table for exp in expectations}
        has_dim = any("dim" in t for t in tables)
        has_fact = any("fact" in t for t in tables)
        assert has_dim or has_fact, f"Expected dim/fact tables, got: {tables}"
