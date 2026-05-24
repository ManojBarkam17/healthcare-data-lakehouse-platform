# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer Ingestion
# MAGIC **Healthcare Data Lakehouse — Databricks Community Edition**
# MAGIC
# MAGIC This notebook ingests raw healthcare data into Bronze Delta tables.
# MAGIC It mirrors the local PySpark pipeline (`src/transformations/bronze/ingest.py`)
# MAGIC but uses Databricks-native features (Unity Catalog, Auto Loader, DBFS).
# MAGIC
# MAGIC ### What this notebook does:
# MAGIC 1. Reads raw CSV/JSON files from DBFS
# MAGIC 2. Adds ingestion metadata columns
# MAGIC 3. Writes to Bronze Delta tables (append-only)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Database and path configuration
CATALOG = "healthcare_lakehouse"
BRONZE_SCHEMA = "bronze"
RAW_PATH = "/FileStore/healthcare/raw/"

# Create catalog and schema (Unity Catalog)
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{BRONZE_SCHEMA}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {BRONZE_SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

from pyspark.sql import functions as F
from datetime import datetime


def ingest_csv_to_bronze(file_name: str, table_name: str) -> None:
    """Ingest a CSV file into a Bronze Delta table with metadata columns."""

    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(f"{RAW_PATH}{file_name}")
    )

    # Add ingestion metadata
    df_with_meta = df.withColumns({
        "_ingested_at": F.current_timestamp(),
        "_source_file": F.lit(file_name),
        "_batch_id": F.lit(datetime.utcnow().strftime("%Y%m%d_%H%M%S")),
    })

    # Write to Delta (append mode — Bronze is append-only)
    (
        df_with_meta.write
        .format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .saveAsTable(f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}")
    )

    row_count = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}").count()
    print(f"Ingested {file_name} -> {table_name}: {row_count} total rows")


def ingest_json_to_bronze(file_name: str, table_name: str) -> None:
    """Ingest a JSON/JSONL file into a Bronze Delta table."""

    df = (
        spark.read
        .option("multiLine", "false")
        .json(f"{RAW_PATH}{file_name}")
    )

    df_with_meta = df.withColumns({
        "_ingested_at": F.current_timestamp(),
        "_source_file": F.lit(file_name),
        "_batch_id": F.lit(datetime.utcnow().strftime("%Y%m%d_%H%M%S")),
    })

    (
        df_with_meta.write
        .format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .saveAsTable(f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}")
    )

    row_count = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}").count()
    print(f"Ingested {file_name} -> {table_name}: {row_count} total rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingest All Sources

# COMMAND ----------

# CSV sources
csv_sources = {
    "members.csv": "raw_members",
    "providers.csv": "raw_providers",
    "payers.csv": "raw_payers",
    "claims_headers.csv": "raw_claims_headers",
    "claims_lines.csv": "raw_claims_lines",
}

for file_name, table_name in csv_sources.items():
    ingest_csv_to_bronze(file_name, table_name)

# JSONL sources
ingest_json_to_bronze("adt_events.jsonl", "raw_adt_events")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Bronze Tables

# COMMAND ----------

# MAGIC %sql
# MAGIC SHOW TABLES IN healthcare_lakehouse.bronze;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check row counts across all Bronze tables
# MAGIC SELECT 'raw_members' as table_name, COUNT(*) as row_count FROM healthcare_lakehouse.bronze.raw_members
# MAGIC UNION ALL
# MAGIC SELECT 'raw_providers', COUNT(*) FROM healthcare_lakehouse.bronze.raw_providers
# MAGIC UNION ALL
# MAGIC SELECT 'raw_payers', COUNT(*) FROM healthcare_lakehouse.bronze.raw_payers
# MAGIC UNION ALL
# MAGIC SELECT 'raw_claims_headers', COUNT(*) FROM healthcare_lakehouse.bronze.raw_claims_headers
# MAGIC UNION ALL
# MAGIC SELECT 'raw_claims_lines', COUNT(*) FROM healthcare_lakehouse.bronze.raw_claims_lines
# MAGIC UNION ALL
# MAGIC SELECT 'raw_adt_events', COUNT(*) FROM healthcare_lakehouse.bronze.raw_adt_events
# MAGIC ORDER BY table_name;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Delta Lake Features
# MAGIC
# MAGIC Bronze tables support time travel for auditing:

# COMMAND ----------

# MAGIC %sql
# MAGIC -- View table history (all operations)
# MAGIC DESCRIBE HISTORY healthcare_lakehouse.bronze.raw_members;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Query data as it existed at a previous version
# MAGIC -- SELECT * FROM healthcare_lakehouse.bronze.raw_members VERSION AS OF 0 LIMIT 5;
