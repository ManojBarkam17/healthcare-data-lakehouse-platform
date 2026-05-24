# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer — Star Schema & SCD Type 2
# MAGIC **Healthcare Data Lakehouse — Databricks Community Edition**
# MAGIC
# MAGIC This notebook builds the Gold layer dimensional model from Silver tables.
# MAGIC It mirrors `src/transformations/gold/build_dimensions.py`.
# MAGIC
# MAGIC ### Tables created:
# MAGIC - `dim_member` (SCD Type 2 with valid_from/valid_to/is_current)
# MAGIC - `dim_provider`, `dim_payer`, `dim_diagnosis`, `dim_procedure`
# MAGIC - `fact_claims` (partitioned by service_year_month)
# MAGIC - `fact_adt_events` (partitioned by event_year_month)

# COMMAND ----------

CATALOG = "healthcare_lakehouse"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}")
spark.sql(f"USE CATALOG {CATALOG}")

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_member (SCD Type 2)
# MAGIC
# MAGIC Tracks member changes over time. Each row represents a version of the member record.
# MAGIC - `valid_from`: When this version became active
# MAGIC - `valid_to`: When this version was superseded (9999-12-31 if current)
# MAGIC - `is_current`: True for the latest version

# COMMAND ----------

silver_members = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.clean_members")

# For initial load, all records are "current"
dim_member = (
    silver_members
    .withColumn("member_key", F.monotonically_increasing_id())
    .withColumn("valid_from", F.coalesce(F.col("effective_date"), F.current_date()))
    .withColumn("valid_to", F.lit("9999-12-31").cast("date"))
    .withColumn("is_current", F.lit(True))
    .select(
        "member_key", "member_id", "first_name", "last_name",
        "date_of_birth", "gender", "state", "zip_code", "plan_type",
        "ssn_hash", "valid_from", "valid_to", "is_current",
    )
)

(
    dim_member.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable(f"{CATALOG}.{GOLD_SCHEMA}.dim_member")
)

print(f"dim_member: {dim_member.count()} rows")
display(dim_member.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_provider

# COMMAND ----------

silver_providers = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.clean_providers")

dim_provider = (
    silver_providers
    .withColumn("provider_key", F.monotonically_increasing_id())
    .select(
        "provider_key", "provider_id", "npi", "first_name", "last_name",
        "specialty", "facility_name", "state", "is_active",
    )
)

dim_provider.write.format("delta").mode("overwrite").saveAsTable(
    f"{CATALOG}.{GOLD_SCHEMA}.dim_provider"
)
print(f"dim_provider: {dim_provider.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_payer

# COMMAND ----------

silver_payers = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.clean_payers")

dim_payer = (
    silver_payers
    .withColumn("payer_key", F.monotonically_increasing_id())
    .select("payer_key", "payer_id", "payer_name", "payer_type", "state", "is_active")
)

dim_payer.write.format("delta").mode("overwrite").saveAsTable(
    f"{CATALOG}.{GOLD_SCHEMA}.dim_payer"
)
print(f"dim_payer: {dim_payer.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_diagnosis & dim_procedure
# MAGIC
# MAGIC Extract distinct ICD-10 and CPT codes from claim lines.

# COMMAND ----------

silver_lines = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.clean_claim_lines")

# Diagnosis dimension
dim_diagnosis = (
    silver_lines
    .select("icd10_code", "icd10_description")
    .dropDuplicates(["icd10_code"])
    .filter(F.col("icd10_code").isNotNull())
    .withColumn("diagnosis_key", F.monotonically_increasing_id())
    .select("diagnosis_key", "icd10_code", F.col("icd10_description").alias("description"))
)

dim_diagnosis.write.format("delta").mode("overwrite").saveAsTable(
    f"{CATALOG}.{GOLD_SCHEMA}.dim_diagnosis"
)
print(f"dim_diagnosis: {dim_diagnosis.count()} rows")

# Procedure dimension
dim_procedure = (
    silver_lines
    .select("cpt_code", "cpt_description")
    .dropDuplicates(["cpt_code"])
    .filter(F.col("cpt_code").isNotNull())
    .withColumn("procedure_key", F.monotonically_increasing_id())
    .select("procedure_key", "cpt_code", F.col("cpt_description").alias("description"))
)

dim_procedure.write.format("delta").mode("overwrite").saveAsTable(
    f"{CATALOG}.{GOLD_SCHEMA}.dim_procedure"
)
print(f"dim_procedure: {dim_procedure.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## fact_claims
# MAGIC
# MAGIC Partitioned by `service_year_month` for query performance.

# COMMAND ----------

silver_claims = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.clean_claims")

# Join with dimension keys
fact_claims = (
    silver_claims
    .join(dim_member.filter("is_current"), "member_id", "left")
    .join(dim_provider, "provider_id", "left")
    .join(dim_payer, "payer_id", "left")
    .withColumn("service_year_month",
        F.date_format(F.col("service_date"), "yyyy-MM")
    )
    .select(
        "claim_id", "member_key", "provider_key", "payer_key",
        F.col("total_charge_amount").alias("claim_amount"),
        F.col("allowed_amount"),
        F.col("paid_amount"),
        "status", "service_date", "submission_date",
        "service_year_month",
    )
)

(
    fact_claims.write
    .format("delta")
    .mode("overwrite")
    .partitionBy("service_year_month")
    .saveAsTable(f"{CATALOG}.{GOLD_SCHEMA}.fact_claims")
)

print(f"fact_claims: {fact_claims.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## fact_adt_events

# COMMAND ----------

silver_adt = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.clean_adt_events")

fact_adt = (
    silver_adt
    .withColumn("event_year_month",
        F.date_format(F.col("event_timestamp"), "yyyy-MM")
    )
    .select(
        "event_id", "event_type", "event_description",
        "facility_name", "department", "room_number",
        "admit_reason", "event_timestamp", "event_year_month",
    )
)

(
    fact_adt.write
    .format("delta")
    .mode("overwrite")
    .partitionBy("event_year_month")
    .saveAsTable(f"{CATALOG}.{GOLD_SCHEMA}.fact_adt_events")
)

print(f"fact_adt_events: {fact_adt.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Gold Layer

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'dim_member' as tbl, COUNT(*) as cnt FROM healthcare_lakehouse.gold.dim_member
# MAGIC UNION ALL SELECT 'dim_provider', COUNT(*) FROM healthcare_lakehouse.gold.dim_provider
# MAGIC UNION ALL SELECT 'dim_payer', COUNT(*) FROM healthcare_lakehouse.gold.dim_payer
# MAGIC UNION ALL SELECT 'dim_diagnosis', COUNT(*) FROM healthcare_lakehouse.gold.dim_diagnosis
# MAGIC UNION ALL SELECT 'dim_procedure', COUNT(*) FROM healthcare_lakehouse.gold.dim_procedure
# MAGIC UNION ALL SELECT 'fact_claims', COUNT(*) FROM healthcare_lakehouse.gold.fact_claims
# MAGIC UNION ALL SELECT 'fact_adt_events', COUNT(*) FROM healthcare_lakehouse.gold.fact_adt_events
# MAGIC ORDER BY tbl;
