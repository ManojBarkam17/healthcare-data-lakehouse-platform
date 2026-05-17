"""CLI entry point for synthetic healthcare data generation.

Usage:
    python -m src.ingestion.generate_data              # default small scale
    python -m src.ingestion.generate_data --scale medium
    python -m src.ingestion.generate_data --scale large
"""

import csv
import json
import random
from pathlib import Path

import click

from src.ingestion.generators import (
    generate_adt_events,
    generate_claims,
    generate_members,
    generate_payers,
    generate_providers,
)
from src.utils.config import SCALES, get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _write_csv(records: list[dict], filepath: Path) -> None:
    """Write a list of dicts to a CSV file."""
    if not records:
        return
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"Wrote {len(records):,} records to {filepath.name}")


def _write_jsonl(records: list[dict], filepath: Path) -> None:
    """Write a list of dicts to a JSON Lines file (one JSON object per line)."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, default=str) + "\n")
    logger.info(f"Wrote {len(records):,} records to {filepath.name}")


@click.command()
@click.option(
    "--scale",
    type=click.Choice(list(SCALES.keys())),
    default=None,
    help="Data volume: small (1K members), medium (10K), large (50K)",
)
def main(scale: str | None) -> None:
    """Generate synthetic healthcare data for the lakehouse pipeline."""
    config = get_config()

    if scale:
        config.scale_name = scale

    config.ensure_dirs()
    data_scale = config.scale
    raw_path = config.raw_path

    logger.info(f"Starting data generation at '{config.scale_name}' scale")
    logger.info(
        f"Targets: {data_scale.members:,} members, {data_scale.providers:,} providers, "
        f"{data_scale.claims:,} claims, {data_scale.adt_events:,} ADT events"
    )

    # 1. Generate payers first (referenced by members and claims)
    payers = generate_payers(data_scale.payers)
    payer_ids = [p["payer_id"] for p in payers]

    # Flatten plan_types_offered for CSV compatibility
    payers_csv = []
    for p in payers:
        row = {**p, "plan_types_offered": "|".join(p["plan_types_offered"])}
        payers_csv.append(row)
    _write_csv(payers_csv, raw_path / "payers.csv")

    # 2. Generate members and link to payers
    members = generate_members(data_scale.members)
    for member in members:
        member["payer_id"] = random.choice(payer_ids)
    member_ids = [m["member_id"] for m in members]
    _write_csv(members, raw_path / "members.csv")

    # 3. Generate providers
    providers = generate_providers(data_scale.providers)
    provider_ids = [p["provider_id"] for p in providers]
    _write_csv(providers, raw_path / "providers.csv")

    # 4. Generate claims (headers + lines)
    claim_headers, claim_lines = generate_claims(
        count=data_scale.claims,
        member_ids=member_ids,
        provider_ids=provider_ids,
        payer_ids=payer_ids,
    )
    _write_csv(claim_headers, raw_path / "claims_headers.csv")
    _write_csv(claim_lines, raw_path / "claims_lines.csv")

    # 5. Generate ADT events (JSON Lines — simulates Kafka topic)
    adt_events = generate_adt_events(
        count=data_scale.adt_events,
        member_ids=member_ids,
        provider_ids=provider_ids,
    )
    _write_jsonl(adt_events, raw_path / "adt_events.jsonl")

    # 6. Create small sample dataset for Streamlit Cloud deployment
    sample_path = config.sample_path
    _write_csv(claim_headers[:500], sample_path / "claims_headers_sample.csv")
    _write_csv(claim_lines[:1000], sample_path / "claims_lines_sample.csv")
    _write_csv(members[:200], sample_path / "members_sample.csv")
    _write_csv(providers[:50], sample_path / "providers_sample.csv")
    _write_csv(payers_csv, sample_path / "payers_sample.csv")
    _write_jsonl(adt_events[:300], sample_path / "adt_events_sample.jsonl")

    logger.info("Data generation complete!")
    logger.info(f"Raw data written to: {raw_path}")
    logger.info(f"Sample data written to: {sample_path}")

    # Summary
    logger.info("--- Summary ---")
    logger.info(f"  Members:       {len(members):>8,}")
    logger.info(f"  Providers:     {len(providers):>8,}")
    logger.info(f"  Payers:        {len(payers):>8,}")
    logger.info(f"  Claim Headers: {len(claim_headers):>8,}")
    logger.info(f"  Claim Lines:   {len(claim_lines):>8,}")
    logger.info(f"  ADT Events:    {len(adt_events):>8,}")


if __name__ == "__main__":
    main()
