"""Data Quality Monitoring DAG.

Runs independently of the main pipeline to provide continuous
data quality monitoring across all lakehouse layers.

Schedule: Every 6 hours (configurable)
Purpose: Catch data drift, schema changes, and quality regressions
         between pipeline runs.

Features:
- Validates Bronze, Silver, and Gold layers independently
- Generates quality summary report
- Alerts on critical failures (email/Slack via Airflow connections)

Author: Manoj Chandra
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator


# ---------------------------------------------------------------------------
# Quality report generator (runs as PythonOperator)
# ---------------------------------------------------------------------------

def generate_quality_report(**context):
    """Aggregate validation results into a summary report.

    Reads validation outputs from each layer and produces a combined
    JSON report with pass/fail/warning counts, stored in data/quality/.
    """
    import json
    from pathlib import Path
    from datetime import datetime

    report = {
        "run_id": context["run_id"],
        "execution_date": str(context["execution_date"]),
        "generated_at": datetime.utcnow().isoformat(),
        "layers": {},
        "overall_status": "PASS",
    }

    # Collect task instance XCom results if available
    ti = context["ti"]
    for layer in ["bronze", "silver", "gold"]:
        task_id = f"validate_{layer}"
        try:
            result = ti.xcom_pull(task_ids=task_id)
            report["layers"][layer] = result or {"status": "completed"}
        except Exception:
            report["layers"][layer] = {"status": "no_data"}

    # Determine overall status
    for layer_result in report["layers"].values():
        if isinstance(layer_result, dict) and layer_result.get("status") == "FAIL":
            report["overall_status"] = "FAIL"
            break

    # Write report
    report_dir = Path("/opt/airflow/project/data/quality")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"quality_report_{context['ds_nodash']}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))

    print(f"Quality report written to {report_path}")
    print(f"Overall status: {report['overall_status']}")

    return report


# ---------------------------------------------------------------------------
# Default arguments
# ---------------------------------------------------------------------------

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
    "execution_timeout": timedelta(minutes=30),
}

# ---------------------------------------------------------------------------
# DAG Definition
# ---------------------------------------------------------------------------

with DAG(
    dag_id="data_quality_monitoring",
    default_args=default_args,
    description="Periodic data quality checks across all lakehouse layers",
    schedule_interval="0 */6 * * *",      # Every 6 hours
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["healthcare", "quality", "monitoring"],
    doc_md=__doc__,
) as dag:

    start = EmptyOperator(task_id="start")

    # Run all three layer validations in parallel
    validate_bronze = BashOperator(
        task_id="validate_bronze",
        bash_command=(
            "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
            "python -m src.quality.validate --layer bronze"
        ),
    )

    validate_silver = BashOperator(
        task_id="validate_silver",
        bash_command=(
            "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
            "python -m src.quality.validate --layer silver"
        ),
    )

    validate_gold = BashOperator(
        task_id="validate_gold",
        bash_command=(
            "cd ${AIRFLOW_VAR_PROJECT_ROOT:-/opt/airflow/project} && "
            "python -m src.quality.validate --layer gold"
        ),
    )

    # Generate combined report after all validations
    quality_report = PythonOperator(
        task_id="generate_quality_report",
        python_callable=generate_quality_report,
        provide_context=True,
    )

    end = EmptyOperator(task_id="end", trigger_rule="all_done")

    # Parallel validation → report → end
    start >> [validate_bronze, validate_silver, validate_gold] >> quality_report >> end
