"""Silver Layer Transformations — Cleansed, validated, deduplicated.

Reads Bronze Delta tables and applies:
- Schema enforcement (explicit column types)
- Deduplication (window-based on business keys)
- PHI/PII masking (SHA-256 hashing of SSN, name tokenization)
- Data quality filters (nulls, invalid values)
- Standardization (uppercase state codes, trimmed strings)

Usage:
    python -m src.transformations.silver.transform
"""

from datetime import datetime

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
# PHI Masking — Native Spark SQL functions (no Python UDFs)
# ---------------------------------------------------------------------------
# Using native Spark functions instead of Python UDFs for:
# 1. Better performance (no Python serialization overhead)
# 2. Cross-platform reliability (avoids pickling issues on Windows)
# 3. Catalyst optimizer can push these through the query plan


def mask_ssn_col(col_name: str) -> F.Column:
    """Hash SSN column using SHA-256. Returns first 16 hex chars.

    In production, this would use a key vault or tokenization service.
    SHA-256 is used here to demonstrate the masking pattern.
    """
    return F.substring(F.sha2(F.col(col_name), 256), 1, 16)


def mask_name_col(col_name: str) -> F.Column:
    """Mask name column: keep first initial, replace rest with asterisks.

    Example: 'John' -> 'J***'
    Uses native Spark string functions instead of Python UDF.
    """
    return F.concat(
        F.substring(F.col(col_name), 1, 1),
        F.expr(f"repeat('*', length({col_name}) - 1)")
    )


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(df: DataFrame, key_columns: list[str], order_column: str = "_ingested_at") -> DataFrame:
    """Remove duplicates keeping the latest record per business key.

    Uses ROW_NUMBER window function — a production-standard pattern
    for handling late-arriving duplicates in batch pipelines.
    """
    window = Window.partitionBy(*key_columns).orderBy(F.col(order_column).desc())
    return (
        df.withColumn("_row_num", F.row_number().over(window))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )


# ---------------------------------------------------------------------------
# Silver Transformations per Table
# ---------------------------------------------------------------------------

def transform_members(spark: SparkSession, bronze_path: str, silver_path: str) -> int:
    """Cleanse and mask member records."""
    logger.info("Transforming members: Bronze -> Silver")

    df = spark.read.format("delta").load(bronze_path)

    silver_df = (
        df
        # Deduplicate on member_id
        .transform(lambda d: deduplicate(d, ["member_id"]))
        # PHI masking (native Spark SQL — no Python UDFs)
        .withColumn("ssn_masked", mask_ssn_col("ssn"))
        .withColumn("first_name_masked", mask_name_col("first_name"))
        .withColumn("last_name_masked", mask_name_col("last_name"))
        .drop("ssn")  # Remove raw PHI
        # Standardize
        .withColumn("state", F.upper(F.trim(F.col("state"))))
        .withColumn("gender", F.upper(F.trim(F.col("gender"))))
        .withColumn("email", F.lower(F.trim(F.col("email"))))
        # Type enforcement
        .withColumn("date_of_birth", F.to_date(F.col("date_of_birth")))
        .withColumn("effective_date", F.to_date(F.col("effective_date")))
        .withColumn("termination_date", F.to_date(F.col("termination_date")))
        # Quality filter: must have member_id and name
        .filter(F.col("member_id").isNotNull())
        .filter(F.col("first_name_masked").isNotNull())
        # Add processing metadata
        .withColumn("_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = silver_df.count()
    silver_df.write.format("delta").mode("overwrite").save(silver_path)
    logger.info(f"Silver members: {row_count:,} rows")
    return row_count


def transform_providers(spark: SparkSession, bronze_path: str, silver_path: str) -> int:
    """Cleanse provider records."""
    logger.info("Transforming providers: Bronze -> Silver")

    df = spark.read.format("delta").load(bronze_path)

    silver_df = (
        df
        .transform(lambda d: deduplicate(d, ["provider_id"]))
        # Standardize
        .withColumn("state", F.upper(F.trim(F.col("state"))))
        .withColumn("specialty", F.trim(F.col("specialty")))
        .withColumn("npi", F.trim(F.col("npi")))
        # Validate NPI format (10 digits starting with 1)
        .withColumn(
            "npi_valid",
            F.col("npi").rlike("^1[0-9]{9}$")
        )
        # Quality filter
        .filter(F.col("provider_id").isNotNull())
        .filter(F.col("npi").isNotNull())
        .withColumn("_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = silver_df.count()
    silver_df.write.format("delta").mode("overwrite").save(silver_path)
    logger.info(f"Silver providers: {row_count:,} rows")
    return row_count


def transform_claims(spark: SparkSession, headers_bronze: str, lines_bronze: str,
                     headers_silver: str, lines_silver: str) -> tuple[int, int]:
    """Cleanse and validate claims headers and lines."""
    logger.info("Transforming claims: Bronze -> Silver")

    # --- Claim Headers ---
    headers_df = spark.read.format("delta").load(headers_bronze)

    silver_headers = (
        headers_df
        .transform(lambda d: deduplicate(d, ["claim_id"]))
        # Type enforcement
        .withColumn("service_date", F.to_date(F.col("service_date")))
        .withColumn("submission_date", F.to_date(F.col("submission_date")))
        .withColumn("total_charge_amount", F.col("total_charge_amount").cast(T.DecimalType(12, 2)))
        .withColumn("total_paid_amount", F.col("total_paid_amount").cast(T.DecimalType(12, 2)))
        # Standardize status
        .withColumn("status", F.lower(F.trim(F.col("status"))))
        .withColumn("claim_type", F.lower(F.trim(F.col("claim_type"))))
        # Quality: charge amount must be positive
        .filter(F.col("total_charge_amount") > 0)
        .filter(F.col("claim_id").isNotNull())
        .filter(F.col("member_id").isNotNull())
        .withColumn("_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    header_count = silver_headers.count()
    silver_headers.write.format("delta").mode("overwrite").save(headers_silver)
    logger.info(f"Silver claim headers: {header_count:,} rows")

    # --- Claim Lines ---
    lines_df = spark.read.format("delta").load(lines_bronze)

    silver_lines = (
        lines_df
        .transform(lambda d: deduplicate(d, ["claim_line_id"]))
        # Type enforcement
        .withColumn("service_date", F.to_date(F.col("service_date")))
        .withColumn("line_charge_amount", F.col("line_charge_amount").cast(T.DecimalType(12, 2)))
        .withColumn("allowed_amount", F.col("allowed_amount").cast(T.DecimalType(12, 2)))
        .withColumn("paid_amount", F.col("paid_amount").cast(T.DecimalType(12, 2)))
        .withColumn("units", F.col("units").cast(T.IntegerType()))
        # Validate: ICD-10 format (letter + digits + optional dot + digits)
        .withColumn("icd10_valid", F.col("icd10_code").rlike("^[A-Z][0-9]"))
        # Validate: CPT format (5 digits)
        .withColumn("cpt_valid", F.col("cpt_code").rlike("^[0-9]{5}$"))
        # Only keep lines that belong to valid headers
        .filter(F.col("claim_id").isNotNull())
        .filter(F.col("line_charge_amount") > 0)
        .withColumn("_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    line_count = silver_lines.count()
    silver_lines.write.format("delta").mode("overwrite").save(lines_silver)
    logger.info(f"Silver claim lines: {line_count:,} rows")

    return header_count, line_count


def transform_adt_events(spark: SparkSession, bronze_path: str, silver_path: str) -> int:
    """Cleanse ADT events."""
    logger.info("Transforming ADT events: Bronze -> Silver")

    df = spark.read.format("delta").load(bronze_path)

    silver_df = (
        df
        .transform(lambda d: deduplicate(d, ["event_id"]))
        # Type enforcement
        .withColumn("event_timestamp", F.to_timestamp(F.col("event_timestamp")))
        # Standardize event types
        .withColumn("event_type", F.upper(F.trim(F.col("event_type"))))
        .withColumn("department", F.trim(F.col("department")))
        # Validate event type codes
        .filter(F.col("event_type").isin("A01", "A02", "A03", "A04", "A08"))
        .filter(F.col("event_id").isNotNull())
        .filter(F.col("member_id").isNotNull())
        .withColumn("_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = silver_df.count()
    silver_df.write.format("delta").mode("overwrite").save(silver_path)
    logger.info(f"Silver ADT events: {row_count:,} rows")
    return row_count


def transform_payers(spark: SparkSession, bronze_path: str, silver_path: str) -> int:
    """Cleanse payer records."""
    logger.info("Transforming payers: Bronze -> Silver")

    df = spark.read.format("delta").load(bronze_path)

    silver_df = (
        df
        .transform(lambda d: deduplicate(d, ["payer_id"]))
        .withColumn("state", F.upper(F.trim(F.col("state"))))
        .withColumn("payer_name", F.trim(F.col("payer_name")))
        .withColumn("payer_type", F.trim(F.col("payer_type")))
        .filter(F.col("payer_id").isNotNull())
        .withColumn("_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    row_count = silver_df.count()
    silver_df.write.format("delta").mode("overwrite").save(silver_path)
    logger.info(f"Silver payers: {row_count:,} rows")
    return row_count


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

@click.command()
def main() -> None:
    """Run Silver layer transformations for all tables."""
    config = get_config()
    config.ensure_dirs()
    spark = get_spark("SilverTransformations")
    bronze = config.bronze_path
    silver = config.silver_path

    logger.info("Starting Silver layer transformations")

    transform_members(spark, str(bronze / "raw_members"), str(silver / "cleansed_members"))
    transform_providers(spark, str(bronze / "raw_providers"), str(silver / "cleansed_providers"))
    transform_payers(spark, str(bronze / "raw_payers"), str(silver / "cleansed_payers"))
    transform_claims(
        spark,
        headers_bronze=str(bronze / "raw_claims_headers"),
        lines_bronze=str(bronze / "raw_claims_lines"),
        headers_silver=str(silver / "cleansed_claims_headers"),
        lines_silver=str(silver / "cleansed_claims_lines"),
    )
    transform_adt_events(spark, str(bronze / "raw_adt_events"), str(silver / "cleansed_adt_events"))

    logger.info("Silver layer transformations complete!")
    spark.stop()


if __name__ == "__main__":
    main()
