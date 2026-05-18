"""Expectation suite definitions for each pipeline layer.

Each suite is a Python function that returns a list of expectations.
This code-driven approach (vs JSON configs) is more portable,
version-control friendly, and easier to review in pull requests.

Healthcare data quality gates:
- Bronze: Schema presence, non-empty tables, required columns exist
- Silver: PHI masking verified, deduplication confirmed, type enforcement
- Gold: Referential integrity, business rule validation, metric bounds
"""

from dataclasses import dataclass


@dataclass
class Expectation:
    """A single data quality expectation."""
    table: str
    check: str
    column: str | None = None
    kwargs: dict | None = None
    severity: str = "critical"  # critical, warning, info


# ---------------------------------------------------------------------------
# Bronze Layer Expectations
# ---------------------------------------------------------------------------

def bronze_expectations() -> list[Expectation]:
    """Bronze layer: raw data landed correctly with metadata."""
    return [
        # --- raw_members ---
        Expectation("raw_members", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 100, "max_value": 50000}),
        Expectation("raw_members", "expect_column_to_exist", column="member_id"),
        Expectation("raw_members", "expect_column_to_exist", column="first_name"),
        Expectation("raw_members", "expect_column_to_exist", column="ssn"),
        Expectation("raw_members", "expect_column_to_exist", column="_ingested_at"),
        Expectation("raw_members", "expect_column_to_exist", column="_source_file"),
        Expectation("raw_members", "expect_column_to_exist", column="_batch_id"),
        Expectation("raw_members", "expect_column_values_to_not_be_null", column="member_id"),

        # --- raw_providers ---
        Expectation("raw_providers", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 50, "max_value": 10000}),
        Expectation("raw_providers", "expect_column_to_exist", column="provider_id"),
        Expectation("raw_providers", "expect_column_to_exist", column="npi"),
        Expectation("raw_providers", "expect_column_values_to_not_be_null", column="provider_id"),

        # --- raw_claims_headers ---
        Expectation("raw_claims_headers", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 1000, "max_value": 500000}),
        Expectation("raw_claims_headers", "expect_column_to_exist", column="claim_id"),
        Expectation("raw_claims_headers", "expect_column_to_exist", column="member_id"),
        Expectation("raw_claims_headers", "expect_column_to_exist", column="total_charge_amount"),

        # --- raw_claims_lines ---
        Expectation("raw_claims_lines", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 1000, "max_value": 1000000}),
        Expectation("raw_claims_lines", "expect_column_to_exist", column="claim_line_id"),
        Expectation("raw_claims_lines", "expect_column_to_exist", column="cpt_code"),
        Expectation("raw_claims_lines", "expect_column_to_exist", column="icd10_code"),

        # --- raw_adt_events ---
        Expectation("raw_adt_events", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 100, "max_value": 100000}),
        Expectation("raw_adt_events", "expect_column_to_exist", column="event_id"),
        Expectation("raw_adt_events", "expect_column_to_exist", column="event_type"),

        # --- raw_payers ---
        Expectation("raw_payers", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 5, "max_value": 1000}),
        Expectation("raw_payers", "expect_column_to_exist", column="payer_id"),
    ]


# ---------------------------------------------------------------------------
# Silver Layer Expectations
# ---------------------------------------------------------------------------

def silver_expectations() -> list[Expectation]:
    """Silver layer: cleansed, deduplicated, PHI masked."""
    return [
        # --- PHI Masking Verification (HIPAA compliance) ---
        # SSN column must NOT exist in silver (dropped after masking)
        Expectation("cleansed_members", "expect_column_to_not_exist", column="ssn",
                     severity="critical"),
        # Masked SSN must exist
        Expectation("cleansed_members", "expect_column_to_exist", column="ssn_masked"),
        # Masked names must exist
        Expectation("cleansed_members", "expect_column_to_exist", column="first_name_masked"),
        Expectation("cleansed_members", "expect_column_to_exist", column="last_name_masked"),

        # --- Deduplication Verification ---
        Expectation("cleansed_members", "expect_column_values_to_be_unique", column="member_id"),
        Expectation("cleansed_providers", "expect_column_values_to_be_unique", column="provider_id"),
        Expectation("cleansed_payers", "expect_column_values_to_be_unique", column="payer_id"),

        # --- Null Checks (post-quality-filter) ---
        Expectation("cleansed_members", "expect_column_values_to_not_be_null", column="member_id"),
        Expectation("cleansed_members", "expect_column_values_to_not_be_null", column="first_name_masked"),
        Expectation("cleansed_providers", "expect_column_values_to_not_be_null", column="npi"),
        Expectation("cleansed_claims_headers", "expect_column_values_to_not_be_null", column="claim_id"),
        Expectation("cleansed_claims_headers", "expect_column_values_to_not_be_null", column="member_id"),

        # --- Type Enforcement ---
        # Charge amounts must be positive (quality filter applied)
        Expectation("cleansed_claims_headers", "expect_column_values_to_be_between",
                     column="total_charge_amount",
                     kwargs={"min_value": 0.01}),
        Expectation("cleansed_claims_lines", "expect_column_values_to_be_between",
                     column="line_charge_amount",
                     kwargs={"min_value": 0.01}),

        # --- Standardization Checks ---
        Expectation("cleansed_members", "expect_column_values_to_match_regex",
                     column="state", kwargs={"regex": "^[A-Z]{2}$"},
                     severity="warning"),
        Expectation("cleansed_members", "expect_column_values_to_be_in_set",
                     column="gender", kwargs={"value_set": ["M", "F", "MALE", "FEMALE"]},
                     severity="warning"),

        # --- ADT Event Type Validation ---
        Expectation("cleansed_adt_events", "expect_column_values_to_be_in_set",
                     column="event_type",
                     kwargs={"value_set": ["A01", "A02", "A03", "A04", "A08"]}),

        # --- Row count sanity (silver should have <= bronze rows) ---
        Expectation("cleansed_members", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 100, "max_value": 50000}),
        Expectation("cleansed_claims_headers", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 1000, "max_value": 500000}),
    ]


# ---------------------------------------------------------------------------
# Gold Layer Expectations
# ---------------------------------------------------------------------------

def gold_expectations() -> list[Expectation]:
    """Gold layer: star schema integrity and business rule validation."""
    return [
        # --- Dimension Completeness ---
        Expectation("dim_member", "expect_column_values_to_not_be_null", column="member_id"),
        Expectation("dim_member", "expect_column_to_exist", column="is_current"),
        Expectation("dim_member", "expect_column_to_exist", column="effective_start"),
        Expectation("dim_member", "expect_column_to_exist", column="effective_end"),
        Expectation("dim_provider", "expect_column_values_to_be_unique", column="provider_id"),
        Expectation("dim_payer", "expect_column_values_to_be_unique", column="payer_id"),

        # --- Fact Table Integrity ---
        Expectation("fact_claims", "expect_column_values_to_not_be_null", column="claim_id"),
        Expectation("fact_claims", "expect_column_values_to_not_be_null", column="member_id"),
        Expectation("fact_claims", "expect_column_values_to_not_be_null", column="provider_id"),
        Expectation("fact_claims", "expect_column_values_to_not_be_null", column="service_date"),

        # --- Financial Bounds ---
        Expectation("fact_claims", "expect_column_values_to_be_between",
                     column="paid_amount",
                     kwargs={"min_value": 0, "max_value": 1000000},
                     severity="warning"),
        Expectation("fact_claims", "expect_column_values_to_be_between",
                     column="line_charge_amount",
                     kwargs={"min_value": 0.01, "max_value": 1000000}),

        # --- Partition Key Presence ---
        Expectation("fact_claims", "expect_column_values_to_not_be_null",
                     column="service_year_month"),
        Expectation("fact_adt_events", "expect_column_values_to_not_be_null",
                     column="event_year_month"),

        # --- Code System Validation ---
        Expectation("dim_diagnosis", "expect_column_values_to_be_in_set",
                     column="code_system",
                     kwargs={"value_set": ["ICD-10-CM"]}),
        Expectation("dim_procedure", "expect_column_values_to_be_in_set",
                     column="code_system",
                     kwargs={"value_set": ["CPT-4"]}),

        # --- Row Counts (Gold should match Silver) ---
        Expectation("dim_member", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 100, "max_value": 50000}),
        Expectation("fact_claims", "expect_table_row_count_to_be_between",
                     kwargs={"min_value": 1000, "max_value": 1000000}),
    ]
