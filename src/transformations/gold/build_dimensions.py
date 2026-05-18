"""Gold Layer — Star schema dimensional model.

Reads Silver Delta tables and builds analytics-ready dimensions and facts:
- dim_member (SCD Type 2 — tracks plan/address changes over time)
- dim_provider
- dim_payer
- dim_diagnosis (from ICD-10 codes in claims)
- dim_procedure (from CPT codes in claims)
- fact_claims
- fact_adt_events

Also exports to DuckDB for dbt and Streamlit consumption.

Usage:
    python -m src.transformations.gold.build_dimensions
"""

from datetime import datetime
from pathlib import Path

import click
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Dimension Builders
# ---------------------------------------------------------------------------

def build_dim_member_scd2(spark: SparkSession, silver_path: str, gold_path: str) -> int:
    """Build dim_member with SCD Type 2 tracking.

    SCD Type 2 tracks historical changes by creating new rows
    when tracked attributes change. Here we track:
    - plan_type changes (member switches insurance plans)
    - address/state changes (member relocates)

    Each row has effective_start, effective_end, and is_current flags.
    """
    logger.info("Building dim_member (SCD Type 2)")

    members = spark.read.format("delta").load(silver_path)

    # For initial load, all members are current
    # In production, this would MERGE against existing dimension
    dim = (
        members
        .select(
            F.monotonically_increasing_id().alias("member_sk"),  # surrogate key
            F.col("member_id"),
            F.col("first_name_masked").alias("first_name"),
            F.col("last_name_masked").alias("last_name"),
            F.col("date_of_birth"),
            F.col("gender"),
            F.col("city"),
            F.col("state"),
            F.col("zip_code"),
            F.col("plan_type"),
            F.col("payer_id"),
            F.col("effective_date"),
            F.col("termination_date"),
        )
        .withColumn("effective_start", F.col("effective_date"))
        .withColumn("effective_end", F.lit("9999-12-31").cast(T.DateType()))
        .withColumn("is_current", F.lit(True))
        .withColumn("_loaded_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = dim.count()
    dim.write.format("delta").mode("overwrite").save(gold_path)
    logger.info(f"dim_member: {row_count:,} rows (SCD2)")
    return row_count


def build_dim_provider(spark: SparkSession, silver_path: str, gold_path: str) -> int:
    """Build dim_provider."""
    logger.info("Building dim_provider")

    providers = spark.read.format("delta").load(silver_path)

    dim = (
        providers
        .select(
            F.monotonically_increasing_id().alias("provider_sk"),
            F.col("provider_id"),
            F.col("npi"),
            F.col("first_name"),
            F.col("last_name"),
            F.col("specialty"),
            F.col("facility_name"),
            F.col("city"),
            F.col("state"),
            F.col("zip_code"),
            F.col("is_active"),
        )
        .withColumn("_loaded_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = dim.count()
    dim.write.format("delta").mode("overwrite").save(gold_path)
    logger.info(f"dim_provider: {row_count:,} rows")
    return row_count


def build_dim_payer(spark: SparkSession, silver_path: str, gold_path: str) -> int:
    """Build dim_payer."""
    logger.info("Building dim_payer")

    payers = spark.read.format("delta").load(silver_path)

    dim = (
        payers
        .select(
            F.monotonically_increasing_id().alias("payer_sk"),
            F.col("payer_id"),
            F.col("payer_name"),
            F.col("payer_type"),
            F.col("state"),
            F.col("is_active"),
        )
        .withColumn("_loaded_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = dim.count()
    dim.write.format("delta").mode("overwrite").save(gold_path)
    logger.info(f"dim_payer: {row_count:,} rows")
    return row_count


def build_dim_diagnosis(spark: SparkSession, claims_silver_path: str, gold_path: str) -> int:
    """Build dim_diagnosis from distinct ICD-10 codes in claims."""
    logger.info("Building dim_diagnosis")

    claims = spark.read.format("delta").load(claims_silver_path)

    dim = (
        claims
        .select(
            F.col("icd10_code"),
            F.col("icd10_description"),
        )
        .distinct()
        .withColumn("diagnosis_sk", F.monotonically_increasing_id())
        .select(
            F.col("diagnosis_sk"),
            F.col("icd10_code").alias("diagnosis_code"),
            F.col("icd10_description").alias("diagnosis_description"),
            F.lit("ICD-10-CM").alias("code_system"),
        )
        .withColumn("_loaded_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = dim.count()
    dim.write.format("delta").mode("overwrite").save(gold_path)
    logger.info(f"dim_diagnosis: {row_count:,} rows")
    return row_count


def build_dim_procedure(spark: SparkSession, claims_silver_path: str, gold_path: str) -> int:
    """Build dim_procedure from distinct CPT codes in claims."""
    logger.info("Building dim_procedure")

    claims = spark.read.format("delta").load(claims_silver_path)

    dim = (
        claims
        .select(
            F.col("cpt_code"),
            F.col("cpt_description"),
        )
        .distinct()
        .withColumn("procedure_sk", F.monotonically_increasing_id())
        .select(
            F.col("procedure_sk"),
            F.col("cpt_code").alias("procedure_code"),
            F.col("cpt_description").alias("procedure_description"),
            F.lit("CPT-4").alias("code_system"),
        )
        .withColumn("_loaded_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = dim.count()
    dim.write.format("delta").mode("overwrite").save(gold_path)
    logger.info(f"dim_procedure: {row_count:,} rows")
    return row_count


# ---------------------------------------------------------------------------
# Fact Builders
# ---------------------------------------------------------------------------

def build_fact_claims(spark: SparkSession, headers_silver: str, lines_silver: str,
                      gold_path: str) -> int:
    """Build fact_claims by joining headers and lines with dimension keys."""
    logger.info("Building fact_claims")

    headers = spark.read.format("delta").load(headers_silver)
    lines = spark.read.format("delta").load(lines_silver)

    fact = (
        lines
        .join(
            headers.select(
                "claim_id", "member_id", "provider_id", "payer_id",
                "claim_type", "status", "denial_reason", "submission_date",
            ),
            on="claim_id",
            how="inner",
        )
        .select(
            F.monotonically_increasing_id().alias("claim_fact_sk"),
            F.col("claim_id"),
            F.col("claim_line_id"),
            F.col("member_id"),
            F.col("provider_id"),
            F.col("payer_id"),
            F.col("claim_type"),
            F.col("status").alias("claim_status"),
            F.col("denial_reason"),
            F.col("service_date"),
            F.col("submission_date"),
            F.col("cpt_code").alias("procedure_code"),
            F.col("icd10_code").alias("diagnosis_code"),
            F.col("line_charge_amount"),
            F.col("allowed_amount"),
            F.col("paid_amount"),
            F.col("units"),
            F.col("line_number"),
        )
        # Partition key for efficient queries
        .withColumn("service_year_month",
                     F.date_format(F.col("service_date"), "yyyy-MM"))
        .withColumn("_loaded_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = fact.count()
    (
        fact.write.format("delta")
        .mode("overwrite")
        .partitionBy("service_year_month")
        .save(gold_path)
    )
    logger.info(f"fact_claims: {row_count:,} rows")
    return row_count


def build_fact_adt_events(spark: SparkSession, silver_path: str, gold_path: str) -> int:
    """Build fact_adt_events."""
    logger.info("Building fact_adt_events")

    events = spark.read.format("delta").load(silver_path)

    fact = (
        events
        .select(
            F.monotonically_increasing_id().alias("adt_fact_sk"),
            F.col("event_id"),
            F.col("event_type"),
            F.col("event_description"),
            F.col("member_id"),
            F.col("provider_id"),
            F.col("facility_name"),
            F.col("department"),
            F.col("room_number"),
            F.col("admit_reason"),
            F.col("event_timestamp"),
            F.date_format(F.col("event_timestamp"), "yyyy-MM").alias("event_year_month"),
        )
        .withColumn("_loaded_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = fact.count()
    (
        fact.write.format("delta")
        .mode("overwrite")
        .partitionBy("event_year_month")
        .save(gold_path)
    )
    logger.info(f"fact_adt_events: {row_count:,} rows")
    return row_count


# ---------------------------------------------------------------------------
# DuckDB Export
# ---------------------------------------------------------------------------

def export_to_duckdb(spark: SparkSession, gold_path: Path, duckdb_path: Path) -> None:
    """Export Gold Delta tables to DuckDB for dbt and Streamlit.

    DuckDB serves as the free, local analytics warehouse.
    In production, this layer would be Snowflake or BigQuery.
    """
    import duckdb

    logger.info(f"Exporting Gold tables to DuckDB: {duckdb_path}")
    con = duckdb.connect(str(duckdb_path))

    tables = [
        "dim_member", "dim_provider", "dim_payer",
        "dim_diagnosis", "dim_procedure",
        "fact_claims", "fact_adt_events",
    ]

    for table_name in tables:
        delta_path = gold_path / table_name
        if not delta_path.exists():
            logger.warning(f"Skipping {table_name} — Delta table not found")
            continue

        df = spark.read.format("delta").load(str(delta_path))
        pandas_df = df.toPandas()
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM pandas_df")
        logger.info(f"  Exported {table_name}: {len(pandas_df):,} rows")

    con.close()
    logger.info("DuckDB export complete")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

@click.command()
def main() -> None:
    """Build Gold layer dimensional model from Silver tables."""
    config = get_config()
    config.ensure_dirs()
    spark = get_spark("GoldDimensions")
    silver = config.silver_path
    gold = config.gold_path

    logger.info("Starting Gold layer build")

    # Dimensions
    build_dim_member_scd2(spark, str(silver / "cleansed_members"), str(gold / "dim_member"))
    build_dim_provider(spark, str(silver / "cleansed_providers"), str(gold / "dim_provider"))
    build_dim_payer(spark, str(silver / "cleansed_payers"), str(gold / "dim_payer"))
    build_dim_diagnosis(spark, str(silver / "cleansed_claims_lines"), str(gold / "dim_diagnosis"))
    build_dim_procedure(spark, str(silver / "cleansed_claims_lines"), str(gold / "dim_procedure"))

    # Facts
    build_fact_claims(
        spark,
        headers_silver=str(silver / "cleansed_claims_headers"),
        lines_silver=str(silver / "cleansed_claims_lines"),
        gold_path=str(gold / "fact_claims"),
    )
    build_fact_adt_events(spark, str(silver / "cleansed_adt_events"), str(gold / "fact_adt_events"))

    # Export to DuckDB
    duckdb_path = config.gold_path / "healthcare_warehouse.duckdb"
    try:
        export_to_duckdb(spark, gold, duckdb_path)
    except ImportError:
        logger.warning("DuckDB not installed — skipping export. Install with: pip install duckdb")
    except Exception as e:
        logger.warning(f"DuckDB export failed: {e}. Pipeline continues — Gold Delta tables are valid.")

    logger.info("Gold layer build complete!")
    spark.stop()


if __name__ == "__main__":
    main()
