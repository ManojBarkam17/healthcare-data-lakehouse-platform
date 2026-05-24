"""Tests for src.utils.config — configuration management."""

import pytest

from src.utils.config import PROJECT_ROOT, SCALES, Config, get_config


class TestDataScale:
    """Tests for DataScale dataclass."""

    def test_small_scale_values(self):
        scale = SCALES["small"]
        assert scale.members == 1_000
        assert scale.providers == 200
        assert scale.payers == 10
        assert scale.claims == 10_000
        assert scale.adt_events == 2_000

    def test_medium_scale_values(self):
        scale = SCALES["medium"]
        assert scale.members == 10_000
        assert scale.providers == 2_000

    def test_large_scale_values(self):
        scale = SCALES["large"]
        assert scale.members == 50_000
        assert scale.claims == 500_000

    def test_scale_is_frozen(self):
        scale = SCALES["small"]
        with pytest.raises(AttributeError):
            scale.members = 999

    def test_all_profiles_exist(self):
        assert set(SCALES.keys()) == {"small", "medium", "large"}


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_paths_exist(self):
        config = Config()
        assert config.raw_path == PROJECT_ROOT / "data" / "raw"
        assert config.bronze_path == PROJECT_ROOT / "data" / "bronze"
        assert config.silver_path == PROJECT_ROOT / "data" / "silver"
        assert config.gold_path == PROJECT_ROOT / "data" / "gold"
        assert config.sample_path == PROJECT_ROOT / "data" / "sample"

    def test_default_scale(self):
        config = Config()
        assert config.scale_name == "small"
        assert config.scale.members == 1_000

    def test_scale_property(self):
        config = Config(scale_name="medium")
        assert config.scale.members == 10_000

    def test_postgres_defaults(self):
        config = Config()
        assert config.pg_host == "localhost"
        assert config.pg_port == 5432
        assert config.pg_db == "healthcare_raw"

    def test_kafka_defaults(self):
        config = Config()
        assert config.kafka_bootstrap == "localhost:9092"
        assert config.kafka_topic_adt == "adt_events"


class TestGetConfig:
    """Tests for get_config factory function."""

    def test_returns_config_instance(self):
        config = get_config()
        assert isinstance(config, Config)

    def test_project_root_is_valid(self):
        assert PROJECT_ROOT.exists()
        assert (PROJECT_ROOT / "src").exists()
