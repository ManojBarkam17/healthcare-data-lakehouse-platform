"""Healthcare Data Lakehouse — Full Pipeline DAG.

Orchestrates the complete medallion architecture pipeline:
  1. Generate synthetic data (or ingest from source)
  2. Bronze layer: Raw CSV/JSONL → Delta Lake (append-only)
  3. Silver layer: Cleanse, deduplicate, mask PHI/PII
  4. Gold layer: Build star-schema dimensions & facts
  5. Export Gold → DuckDB warehouse
  6. dbt transformations: Staging → Intermediate → Marts
  7. Data quality validation on all layers

Schedule: Daily at 06:00 UTC (configurable via Airflow Variables)

DAG Graph:
  generate_data → bronze_ingest → silver_transform → gold_build
     → export_duckdb → dbt_run → dbt_test → validate_quality

Author: Manoj Chandra
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup

# ---------------------------------------------------------------------------
# Default arguments — applied to every task in this DAG
# ---------------------------------------------------------------------------

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

# ---------------------------------------------------------------------------
# DAG Definition
# ---------------------------------------------------------------------------

with DAG(
    dag_id="healthcare_pipeline",
    default_args=default_args,
    description="End-to-end healthcare data lakehouse pipeline (Bronze → Silver → Gold → dbt → QA)",
    schedule_interval="0 6 * * *",       # Daily at 06:00 UTC
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["healthcare", "lakehouse", "medallion", "production"],
    doc_md=__doc__,
) as dag:

    # -----------------------------------------------------------------------
    # Bookend tasks
    # -----------------------------------------------------------------------

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end", trigger_rule="all_success")

    # -----------------------------------------------------------------------
    # Task Group: Data Ingestion
    # -----------------------------------------------------------------------

    with TaskGroup("ingestion", tooltip="Generate or ingest raw data") as ingestion_group:

        generate_data = BashOperator(
            task_id="generate_synthetic_data",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
                "python -m src.ingestion.generate_data"
            ),
            doc_md="Generate synthetic healthcare data (members, providers, payers, claims, ADT events).",
        )

    # -----------------------------------------------------------------------
    # Task Group: Bronze Layer
    # -----------------------------------------------------------------------

    with TaskGroup("bronze", tooltip="Raw → Delta Lake (append-only)") as bronze_group:

        bronze_ingest = BashOperator(
            task_id="ingest_to_delta",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
                "python -m src.transformations.bronze.ingest"
            ),
            doc_md="Ingest raw CSV/JSONL into Bronze Delta tables with metadata columns.",
        )

    # -----------------------------------------------------------------------
    # Task Group: Silver Layer
    # -----------------------------------------------------------------------

    with TaskGroup("silver", tooltip="Cleanse, deduplicate, mask PHI") as silver_group:

        silver_transform = BashOperator(
            task_id="transform_silver",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
                "python -m src.transformations.silver.transform"
            ),
            doc_md="Apply schema enforcement, dedup, PHI masking, and data quality filters.",
        )

    # -----------------------------------------------------------------------
    # Task Group: Gold Layer
    # -----------------------------------------------------------------------

    with TaskGroup("gold", tooltip="Star-schema dimensions & facts") as gold_group:

        gold_build = BashOperator(
            task_id="build_dimensions_facts",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
                "python -m src.transformations.gold.build_dimensions"
            ),
            doc_md="Build dim_member (SCD2), dim_provider, dim_payer, dim_diagnosis, dim_procedure, fact_claims, fact_adt_events.",
        )

        export_duckdb = BashOperator(
            task_id="export_to_duckdb",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
                "python export_to_duckdb.py"
            ),
            doc_md="Export Gold parquet tables to DuckDB for analytics queries.",
        )

        gold_build >> export_duckdb

    # -----------------------------------------------------------------------
    # Task Group: dbt Transformations
    # -----------------------------------------------------------------------

    with TaskGroup("dbt", tooltip="dbt staging → intermediate → marts") as dbt_group:

        dbt_deps = BashOperator(
            task_id="dbt_deps",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project}/dbt_project && "
                "dbt deps --profiles-dir ."
            ),
            doc_md="Install dbt packages (dbt_utils).",
        )

        dbt_run = BashOperator(
            task_id="dbt_run",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project}/dbt_project && "
                "dbt run --profiles-dir . --full-refresh"
            ),
            doc_md="Run all dbt models: staging → intermediate → marts.",
        )

        dbt_test = BashOperator(
            task_id="dbt_test",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project}/dbt_project && "
                "dbt test --profiles-dir ."
            ),
            doc_md="Run dbt tests (schema tests + custom assertions).",
        )

        dbt_deps >> dbt_run >> dbt_test

    # -----------------------------------------------------------------------
    # Task Group: Data Quality
    # -----------------------------------------------------------------------

    with TaskGroup("quality", tooltip="Great Expectations validation") as quality_group:

        validate_bronze = BashOperator(
            task_id="validate_bronze",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
                "python -m src.quality.validate --layer bronze"
            ),
            doc_md="Validate Bronze layer: row counts, required columns, ingestion metadata.",
        )

        validate_silver = BashOperator(
            task_id="validate_silver",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
                "python -m src.quality.validate --layer silver"
            ),
            doc_md="Validate Silver layer: PHI masking, dedup, type enforcement.",
        )

        validate_gold = BashOperator(
            task_id="validate_gold",
            bash_command=(
                "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
                "python -m src.quality.validate --layer gold"
            ),
            doc_md="Validate Gold layer: referential integrity, business rules, financial bounds.",
        )

        [validate_bronze, validate_silver, validate_gold]

    # -----------------------------------------------------------------------
    # DAG Dependency Chain
    # -----------------------------------------------------------------------

    start >> ingestion_group >> bronze_group >> silver_group >> gold_group >> dbt_group >> quality_group >> end
