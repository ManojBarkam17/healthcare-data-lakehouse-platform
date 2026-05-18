"""Data quality validation runner.

Runs expectation suites against Bronze, Silver, and Gold layers
using DuckDB for lightweight validation (no Spark required).

This is a simplified, portable validation engine that demonstrates
the Great Expectations pattern without requiring a full GX deployment.
In production, this would integrate with the GX Data Context and
produce HTML Data Docs.

Usage:
    python -m src.quality.validate              # validate all layers
    python -m src.quality.validate --layer bronze
    python -m src.quality.validate --layer silver
    python -m src.quality.validate --layer gold
"""

import sys
from datetime import datetime
from pathlib import Path

import click
import duckdb

from src.quality.expectations import (
    Expectation,
    bronze_expectations,
    gold_expectations,
    silver_expectations,
)
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Validation Engine
# ---------------------------------------------------------------------------

class ValidationResult:
    """Result of a single expectation check."""

    def __init__(self, expectation: Expectation, passed: bool,
                 observed_value: str = "", message: str = ""):
        self.expectation = expectation
        self.passed = passed
        self.observed_value = observed_value
        self.message = message

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        col = f".{self.expectation.column}" if self.expectation.column else ""
        return f"  [{status}] {self.expectation.table}{col}: {self.expectation.check} {self.message}"


def _run_expectation_duckdb(con: duckdb.DuckDBPyConnection, exp: Expectation) -> ValidationResult:
    """Execute a single expectation against DuckDB."""

    table = exp.table
    column = exp.column
    kwargs = exp.kwargs or {}

    try:
        # --- Row count checks ---
        if exp.check == "expect_table_row_count_to_be_between":
            result = con.execute(f"SELECT count(*) FROM {table}").fetchone()
            count = result[0]
            min_val = kwargs.get("min_value", 0)
            max_val = kwargs.get("max_value", float("inf"))
            passed = min_val <= count <= max_val
            return ValidationResult(exp, passed, str(count),
                                    f"(count={count:,}, expected {min_val:,}-{max_val:,})")

        # --- Column existence ---
        elif exp.check == "expect_column_to_exist":
            cols = [c[0] for c in con.execute(f"DESCRIBE {table}").fetchall()]
            passed = column.lower() in [c.lower() for c in cols]
            return ValidationResult(exp, passed, str(cols),
                                    f"({'found' if passed else 'NOT FOUND'})")

        elif exp.check == "expect_column_to_not_exist":
            cols = [c[0].lower() for c in con.execute(f"DESCRIBE {table}").fetchall()]
            passed = column.lower() not in cols
            return ValidationResult(exp, passed, str(cols),
                                    f"({'correctly absent' if passed else 'STILL EXISTS — PHI leak!'})")

        # --- Null checks ---
        elif exp.check == "expect_column_values_to_not_be_null":
            result = con.execute(
                f"SELECT count(*) FROM {table} WHERE {column} IS NULL"
            ).fetchone()
            null_count = result[0]
            passed = null_count == 0
            return ValidationResult(exp, passed, str(null_count),
                                    f"(nulls={null_count:,})")

        # --- Uniqueness ---
        elif exp.check == "expect_column_values_to_be_unique":
            result = con.execute(f"""
                SELECT count(*) - count(distinct {column}) FROM {table}
            """).fetchone()
            dup_count = result[0]
            passed = dup_count == 0
            return ValidationResult(exp, passed, str(dup_count),
                                    f"(duplicates={dup_count:,})")

        # --- Value range ---
        elif exp.check == "expect_column_values_to_be_between":
            min_val = kwargs.get("min_value")
            max_val = kwargs.get("max_value")
            conditions = []
            if min_val is not None:
                conditions.append(f"{column} < {min_val}")
            if max_val is not None:
                conditions.append(f"{column} > {max_val}")
            where = " OR ".join(conditions) if conditions else "1=0"
            result = con.execute(
                f"SELECT count(*) FROM {table} WHERE {where}"
            ).fetchone()
            violation_count = result[0]
            passed = violation_count == 0
            return ValidationResult(exp, passed, str(violation_count),
                                    f"(violations={violation_count:,})")

        # --- Value set ---
        elif exp.check == "expect_column_values_to_be_in_set":
            value_set = kwargs.get("value_set", [])
            placeholders = ", ".join(f"'{v}'" for v in value_set)
            result = con.execute(f"""
                SELECT count(*) FROM {table}
                WHERE {column} NOT IN ({placeholders})
                  AND {column} IS NOT NULL
            """).fetchone()
            violation_count = result[0]
            passed = violation_count == 0
            return ValidationResult(exp, passed, str(violation_count),
                                    f"(out_of_set={violation_count:,})")

        # --- Regex match ---
        elif exp.check == "expect_column_values_to_match_regex":
            regex = kwargs.get("regex", ".*")
            result = con.execute(f"""
                SELECT count(*) FROM {table}
                WHERE NOT regexp_matches({column}, '{regex}')
                  AND {column} IS NOT NULL
            """).fetchone()
            violation_count = result[0]
            passed = violation_count == 0
            return ValidationResult(exp, passed, str(violation_count),
                                    f"(regex_fails={violation_count:,})")

        else:
            return ValidationResult(exp, True, "skipped",
                                    f"(unsupported check: {exp.check})")

    except Exception as e:
        return ValidationResult(exp, False, "error", f"(ERROR: {e})")


# ---------------------------------------------------------------------------
# Layer Runners
# ---------------------------------------------------------------------------

def _load_delta_to_duckdb(con: duckdb.DuckDBPyConnection, layer_path: Path, tables: list[str]) -> None:
    """Load Delta/Parquet tables into DuckDB for validation."""
    for table_name in tables:
        table_path = layer_path / table_name
        if not table_path.exists():
            logger.warning(f"Skipping {table_name} — path not found: {table_path}")
            continue
        # Delta tables contain parquet files in the root directory
        parquet_files = list(table_path.glob("*.parquet"))
        if parquet_files:
            con.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT * FROM parquet_scan('{table_path}/*.parquet')
            """)


def validate_layer(layer: str, config) -> list[ValidationResult]:
    """Run all expectations for a given layer."""
    con = duckdb.connect(":memory:")
    results = []

    if layer == "bronze":
        tables = ["raw_members", "raw_providers", "raw_payers",
                   "raw_claims_headers", "raw_claims_lines", "raw_adt_events"]
        _load_delta_to_duckdb(con, config.bronze_path, tables)
        expectations = bronze_expectations()

    elif layer == "silver":
        tables = ["cleansed_members", "cleansed_providers", "cleansed_payers",
                   "cleansed_claims_headers", "cleansed_claims_lines", "cleansed_adt_events"]
        _load_delta_to_duckdb(con, config.silver_path, tables)
        expectations = silver_expectations()

    elif layer == "gold":
        # Gold tables are already in DuckDB
        gold_db = config.gold_path / "healthcare_warehouse.duckdb"
        if gold_db.exists():
            con.close()
            con = duckdb.connect(str(gold_db), read_only=True)
        else:
            # Fall back to loading parquet from Delta tables
            tables = ["dim_member", "dim_provider", "dim_payer",
                       "dim_diagnosis", "dim_procedure",
                       "fact_claims", "fact_adt_events"]
            _load_delta_to_duckdb(con, config.gold_path, tables)
        expectations = gold_expectations()

    else:
        logger.error(f"Unknown layer: {layer}")
        return []

    for exp in expectations:
        result = _run_expectation_duckdb(con, exp)
        results.append(result)

    con.close()
    return results


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

def print_report(layer: str, results: list[ValidationResult]) -> tuple[int, int, int]:
    """Print validation results and return (passed, failed, warnings)."""
    passed = sum(1 for r in results if r.passed)
    failed_critical = sum(1 for r in results if not r.passed and r.expectation.severity == "critical")
    failed_warning = sum(1 for r in results if not r.passed and r.expectation.severity == "warning")

    logger.info(f"\n{'='*60}")
    logger.info(f"  {layer.upper()} LAYER VALIDATION REPORT")
    logger.info(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info(f"{'='*60}")

    for result in results:
        logger.info(str(result))

    logger.info(f"\n  Summary: {passed} passed, {failed_critical} failed, {failed_warning} warnings")
    logger.info(f"  Status: {'PASSED' if failed_critical == 0 else 'FAILED'}")
    logger.info(f"{'='*60}\n")

    return passed, failed_critical, failed_warning


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--layer", type=click.Choice(["bronze", "silver", "gold", "all"]),
              default="all", help="Which layer to validate")
def main(layer: str) -> None:
    """Run data quality validation across pipeline layers."""
    config = get_config()

    layers = ["bronze", "silver", "gold"] if layer == "all" else [layer]

    total_passed = 0
    total_failed = 0
    total_warnings = 0

    logger.info("Starting data quality validation")

    for l in layers:
        results = validate_layer(l, config)
        p, f, w = print_report(l, results)
        total_passed += p
        total_failed += f
        total_warnings += w

    logger.info(f"Overall: {total_passed} passed, {total_failed} failed, {total_warnings} warnings")

    if total_failed > 0:
        logger.error("VALIDATION FAILED — critical expectations not met")
        sys.exit(1)
    else:
        logger.info("ALL VALIDATIONS PASSED")


if __name__ == "__main__":
    main()
