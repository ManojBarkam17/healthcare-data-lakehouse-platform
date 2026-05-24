"""Bronze Layer Ingestion — Raw data to Delta Lake.

Reads raw CSV and JSONL files from data/raw/ and writes them as
append-only Delta Lake tables in data/bronze/. This is the first
layer of the medallion architecture.

Bronze layer principles:
- Append-only: never modify or delete source records
- Schema-on-read: preserve original schema as-is
- Add ingestion metadata: _ingested_at, _source_file, _batch_id
- No transformations: raw data exactly as received

Usage:
    python -m src.transformations.bronze.ingest
"""

import uuid
from datetime import datetime
from pathlib import Path

import click
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark

logger = get_logger(__name__)


def _add_ingestion_metadata(df: DataFrame, source_file: str, batch_id: str) -> DataFrame:
    """Add standard metadata columns to every Bronze table.

    These columns enable:
    - Lineage tracking: which file produced each row
    - Reprocessing: identify and replay specific batches
    - Auditing: when data arrived in the lakehouse
    """
    return (
        df
        .withColumn("_ingested_at", F.lit(datetime.utcnow().isoformat()))
        .withColumn("_source_file", F.lit(source_file))
        .withColumn("_batch_id", F.lit(batch_id))
    )


def ingest_csv_to_delta(
    spark: SparkSession,
    source_path: Path,
    target_path: Path,
    table_name: str,
    batch_id: str,
) -> int:
    """Ingest a CSV file into a Bronze Delta table.

    Args:
        spark: Active SparkSession
        source_path: Path to the source CSV file
        target_path: Path to write the Delta table
        table_name: Logical name for logging
        batch_id: Unique identifier for this ingestion run

    Returns:
        Number of rows ingested
    """
    if not source_path.exists():
        logger.warning(f"Source file not found: {source_path}")
        return 0

    logger.info(f"Ingesting {table_name} from {source_path.name}")

    df = (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .option("multiLine", "true")
        .option("escape", '"')
        .load(str(source_path))
    )

    df = _add_ingestion_metadata(df, source_path.name, batch_id)
    row_count = df.count()

    (
        df.write.format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .save(str(target_path))
    )

    logger.info(f"Ingested {row_count:,} rows into bronze.{table_name}")
    return row_count


def ingest_jsonl_to_delta(
    spark: SparkSession,
    source_path: Path,
    target_path: Path,
    table_name: str,
    batch_id: str,
) -> int:
    """Ingest a JSON Lines file into a Bronze Delta table.

    JSON Lines format (one JSON object per line) simulates
    how Kafka messages would land after batch consumption.
    """
    if not source_path.exists():
        logger.warning(f"Source file not found: {source_path}")
        return 0

    logger.info(f"Ingesting {table_name} from {source_path.name}")

    df = (
        spark.read.format("json")
        .option("multiLine", "false")  # JSON Lines = one object per line
        .load(str(source_path))
    )

    df = _add_ingestion_metadata(df, source_path.name, batch_id)
    row_count = df.count()

    (
        df.write.format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .save(str(target_path))
    )

    logger.info(f"Ingested {row_count:,} rows into bronze.{table_name}")
    return row_count


@click.command()
def main() -> None:
    """Run Bronze layer ingestion for all source tables."""
    config = get_config()
    config.ensure_dirs()
    spark = get_spark("BronzeIngestion")
    batch_id = str(uuid.uuid4())[:8]

    logger.info(f"Starting Bronze ingestion — batch_id={batch_id}")
    raw = config.raw_path
    bronze = config.bronze_path
    total_rows = 0

    # --- CSV sources (batch ingestion pattern) ---
    csv_sources = [
        ("members.csv", "raw_members"),
        ("providers.csv", "raw_providers"),
        ("payers.csv", "raw_payers"),
        ("claims_headers.csv", "raw_claims_headers"),
        ("claims_lines.csv", "raw_claims_lines"),
    ]

    for filename, table_name in csv_sources:
        rows = ingest_csv_to_delta(
            spark=spark,
            source_path=raw / filename,
            target_path=bronze / table_name,
            table_name=table_name,
            batch_id=batch_id,
        )
        total_rows += rows

    # --- JSONL source (simulated streaming ingestion) ---
    rows = ingest_jsonl_to_delta(
        spark=spark,
        source_path=raw / "adt_events.jsonl",
        target_path=bronze / "raw_adt_events",
        table_name="raw_adt_events",
        batch_id=batch_id,
    )
    total_rows += rows

    # --- Summary ---
    logger.info("Bronze ingestion complete!")
    logger.info(f"Total rows ingested: {total_rows:,}")
    logger.info(f"Batch ID: {batch_id}")
    logger.info(f"Delta tables written to: {bronze}")

    # Print table stats
    logger.info("--- Table Summary ---")
    for _, table_name in csv_sources:
        table_path = bronze / table_name
        if table_path.exists():
            df = spark.read.format("delta").load(str(table_path))
            logger.info(f"  {table_name}: {df.count():,} rows, {len(df.columns)} columns")

    adt_path = bronze / "raw_adt_events"
    if adt_path.exists():
        df = spark.read.format("delta").load(str(adt_path))
        logger.info(f"  raw_adt_events: {df.count():,} rows, {len(df.columns)} columns")

    spark.stop()


if __name__ == "__main__":
    main()
