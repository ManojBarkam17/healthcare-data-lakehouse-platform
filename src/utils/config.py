"""Centralized configuration for the healthcare data lakehouse."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root: two levels up from src/utils/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class DataScale:
    """Controls the volume of synthetic data generated."""

    members: int
    providers: int
    payers: int
    claims: int
    adt_events: int


# Pre-defined scale profiles
SCALES: dict[str, DataScale] = {
    "small": DataScale(
        members=1_000,
        providers=200,
        payers=10,
        claims=10_000,
        adt_events=2_000,
    ),
    "medium": DataScale(
        members=10_000,
        providers=2_000,
        payers=20,
        claims=100_000,
        adt_events=15_000,
    ),
    "large": DataScale(
        members=50_000,
        providers=5_000,
        payers=30,
        claims=500_000,
        adt_events=50_000,
    ),
}


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # Paths
    raw_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "raw")
    bronze_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "bronze")
    silver_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "silver")
    gold_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "gold")
    sample_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "sample")

    # PostgreSQL
    pg_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    pg_db: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "healthcare_raw"))
    pg_user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "lakehouse"))
    pg_password: str = field(
        default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "changeme")
    )

    # Kafka
    kafka_bootstrap: str = field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    )
    kafka_topic_adt: str = field(
        default_factory=lambda: os.getenv("KAFKA_TOPIC_ADT", "adt_events")
    )

    # Data scale
    scale_name: str = field(default_factory=lambda: os.getenv("DATA_SCALE", "small"))

    @property
    def scale(self) -> DataScale:
        return SCALES[self.scale_name]

    def ensure_dirs(self) -> None:
        """Create data directories if they don't exist."""
        for path in [self.raw_path, self.bronze_path, self.silver_path, self.gold_path, self.sample_path]:
            path.mkdir(parents=True, exist_ok=True)


def get_config() -> Config:
    """Factory function for Config — single access point."""
    return Config()
