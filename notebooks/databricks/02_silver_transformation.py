# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer Transformation
# MAGIC **Healthcare Data Lakehouse — Databricks Community Edition**
# MAGIC
# MAGIC This notebook transforms Bronze data into Silver (cleansed) tables.
# MAGIC It mirrors `src/transformations/silver/transform.py` with Databricks-native features.
# MAGIC
# MAGIC ### Transformations applied:
# MAGIC 1. Schema enforcement with explicit column selection
# MAGIC 2. Deduplication using window functions
# MAGIC 3. PHI/PII masking (SHA-256 for SSN, name tokenization)
# MAGIC 4. Data quality filtering

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "healthcare_lakehouse"
BRONZE_SCHEMA = "bronze"
SILVER_SCHEMA = "silver"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SILVER_SCHEMA}")
spark.sql(f"USE CATALOG {CATALOG}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## PHI Masking Functions
# MAGIC
# MAGIC Using native Spark SQL functions (not Python UDFs) for performance:
# MAGIC - **SSN**: SHA-256 hash (irreversible, HIPAA-compliant)
# MAGIC - **Names**: First character preserved + masked remainder

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window


def mask_phi_columns(df):
    """Apply PHI masking to member data using native Spark SQL."""
    return df.withColumns({
        # SSN: Irreversible SHA-256 hash
        "ssn_hash": F.sha2(F.col("ssn"), 256),

        # Names: First char + asterisks (e.g., "John" -> "J***")
        "first_name": F.concat(
            F.substring(F.col("first_name"), 1, 1),
            F.expr("repeat('*', length(first_name) - 1)")
        ),
        "last_name": F.concat(
            F.substring(F.col("last_name"), 1, 1),
            F.expr("repeat('*', length(last_name) - 1)")
        ),
    }).drop("ssn")  # Remove raw SSN entirely

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform Members

# COMMAND ----------

# Read Bronze members
bronze_members = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.raw_members")

# Schema enforcement: select only expected columns with types
silver_members = (
    bronze_members
    .select(
        F.col("member_id"),
        F.col("first_name"),
        F.col("last_name"),
        F.col("date_of_birth").cast("date"),
        F.col("gender"),
        F.col("ssn"),
        F.col("state"),
        F.col("zip_code"),
        F.col("plan_type"),
        F.col("effective_date").cast("date"),
        F.col("termination_date").cast("date"),
    )
    .filter(F.col("member_id").isNotNull())
    .dropDuplicates(["member_id"])
)

# Apply PHI masking
silver_members = mask_phi_columns(silver_members)

# Write to Silver
(
    silver_members.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable(f"{CATALOG}.{SILVER_SCHEMA}.clean_members")
)

print(f"Silver members: {silver_members.count()} rows")
display(silver_members.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform Claims

# COMMAND ----------

# Read Bronze claims
bronze_claims = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.raw_claims_headers")

# Deduplication: keep latest record per claim_id
dedup_window = Window.partitionBy("claim_id").orderBy(F.col("_ingested_at").desc())

silver_claims = (
    bronze_claims
    .withColumn("_row_num", F.row_number().over(dedup_window))
    .filter(F.col("_row_num") == 1)
    .drop("_row_num", "_ingested_at", "_source_file", "_batch_id")
    .filter(F.col("claim_id").isNotNull())
    .filter(F.col("member_id").isNotNull())
)

(
    silver_claims.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable(f"{CATALOG}.{SILVER_SCHEMA}.clean_claims")
)

print(f"Silver claims: {silver_claims.count()} rows (after dedup)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform Claim Lines

# COMMAND ----------

bronze_lines = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.raw_claims_lines")

silver_lines = (
    bronze_lines
    .filter(F.col("claim_id").isNotNull())
    .filter(F.col("line_charge_amount") > 0)
    .drop("_ingested_at", "_source_file", "_batch_id")
    .dropDuplicates(["claim_line_id"])
)

(
    silver_lines.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable(f"{CATALOG}.{SILVER_SCHEMA}.clean_claim_lines")
)

print(f"Silver claim lines: {silver_lines.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transform Providers, Payers, ADT Events

# COMMAND ----------

# Providers
bronze_providers = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.raw_providers")
silver_providers = (
    bronze_providers
    .filter(F.col("provider_id").isNotNull())
    .dropDuplicates(["provider_id"])
    .drop("_ingested_at", "_source_file", "_batch_id")
)
silver_providers.write.format("delta").mode("overwrite").saveAsTable(
    f"{CATALOG}.{SILVER_SCHEMA}.clean_providers"
)
print(f"Silver providers: {silver_providers.count()} rows")

# Payers
bronze_payers = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.raw_payers")
silver_payers = (
    bronze_payers
    .filter(F.col("payer_id").isNotNull())
    .dropDuplicates(["payer_id"])
    .drop("_ingested_at", "_source_file", "_batch_id")
)
silver_payers.write.format("delta").mode("overwrite").saveAsTable(
    f"{CATALOG}.{SILVER_SCHEMA}.clean_payers"
)
print(f"Silver payers: {silver_payers.count()} rows")

# ADT Events
bronze_adt = spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.raw_adt_events")
silver_adt = (
    bronze_adt
    .filter(F.col("event_id").isNotNull())
    .dropDuplicates(["event_id"])
    .drop("_ingested_at", "_source_file", "_batch_id")
)
silver_adt.write.format("delta").mode("overwrite").saveAsTable(
    f"{CATALOG}.{SILVER_SCHEMA}.clean_adt_events"
)
print(f"Silver ADT events: {silver_adt.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify PHI Masking

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Verify SSN is hashed (should be 64-char hex string)
# MAGIC SELECT member_id, first_name, last_name, ssn_hash, LENGTH(ssn_hash) as hash_length
# MAGIC FROM healthcare_lakehouse.silver.clean_members
# MAGIC LIMIT 5;
