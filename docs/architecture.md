# Architecture Documentation

## System Overview

The Healthcare Data Lakehouse Platform implements a medallion architecture pattern using PySpark and Delta Lake for data processing, with DuckDB as the analytics warehouse and dbt for transformation management.

## Pipeline Architecture

### End-to-End Flow

```
Raw Sources → Bronze (Delta) → Silver (Cleansed) → Gold (Star Schema) → DuckDB → Streamlit
     |              |                |                    |                  |          |
  CSV/JSONL    Append-only      PHI Masking          SCD Type 2        Analytics   4 Pages
  Faker Gen    Full Audit       Dedup + QA          5 Dims + 2 Facts    Engine    Plotly Charts
```

### Processing Engine

PySpark 3.5 with Delta Lake 3.1 handles all transformations. The SparkSession factory (`src/utils/spark_session.py`) provides:

- Automatic Hadoop winutils configuration on Windows
- Delta Lake extension loading via `configure_spark_with_delta_pip`
- Optimized settings for local development (4 shuffle partitions, adaptive query disabled)

### Data Storage

| Layer | Format | Location | Retention |
|-------|--------|----------|-----------|
| Raw | CSV, JSONL | `data/raw/` | Source files |
| Bronze | Delta Lake (Parquet + transaction log) | `data/bronze/` | Append-only, full history |
| Silver | Parquet | `data/silver/` | Latest cleansed version |
| Gold | Parquet (partitioned) | `data/gold/` | Star schema tables |
| Warehouse | DuckDB | `data/gold/warehouse.duckdb` | Analytics-ready |
| Sample | DuckDB | `data/sample/sample_warehouse.duckdb` | For Streamlit Cloud |

### Partitioning Strategy

- `fact_claims`: Partitioned by `service_year_month` (Hive-style)
- `fact_adt_events`: Partitioned by `event_year_month` (Hive-style)
- Non-partitioned: All dimension tables (small enough for full scans)

## Transformation Details

### Bronze Layer

The Bronze ingest module (`src/transformations/bronze/ingest.py`) handles:

- **CSV sources**: members, providers, payers, claims_headers, claims_lines
- **JSONL sources**: adt_events
- **Metadata columns added**: `_ingested_at` (timestamp), `_source_file` (filename)
- **Write mode**: Append (Delta Lake) — nothing is ever overwritten or deleted

### Silver Layer

The Silver transform module (`src/transformations/silver/transform.py`) applies:

1. **Schema enforcement**: Explicit column selection and type casting
2. **Deduplication**: Window function on `claim_id` + `service_date`, keeping latest
3. **PHI masking**:
   - SSN: `SHA-256(ssn)` producing 64-character hex hash (irreversible)
   - Names: First character preserved + masked remainder (e.g., "John" → "J***")
   - Implementation uses native Spark SQL (`F.sha2`, `F.substring`, `F.expr`) for performance
4. **Quality gates**: Records failing critical checks are quarantined

### Gold Layer

The Gold build module (`src/transformations/gold/build_dimensions.py`) creates:

**Dimensions:**
- `dim_member` — SCD Type 2 with `valid_from`, `valid_to`, `is_current` columns
- `dim_provider` — Provider demographics, NPI, specialty, facility
- `dim_payer` — Insurance plan details
- `dim_diagnosis` — ICD-10 codes with descriptions
- `dim_procedure` — CPT codes with descriptions

**Facts:**
- `fact_claims` — Claim-level metrics (charge, allowed, paid amounts, status)
- `fact_adt_events` — Admit/Discharge/Transfer events with timestamps

### SCD Type 2 Implementation

Member dimension tracks changes over time:

```
member_id | state | plan_type | valid_from  | valid_to    | is_current
MBR100001 | TX    | HMO       | 2024-01-01  | 2024-06-30  | false
MBR100001 | CA    | PPO       | 2024-07-01  | 9999-12-31  | true
```

This enables point-in-time queries: "What plan was member X on when this claim was submitted?"

## dbt Architecture

### Model Layers

```
Sources (DuckDB tables)
    └── Staging (7 models) — Type casting, column renaming
         └── Intermediate (4 models) — Joins, aggregations, business logic
              └── Marts (5 models) — Final analytics tables
```

### Key Models

- `int_claims_enriched`: Joins claims with members, providers, payers, diagnoses
- `int_member_claims_summary`: Per-member aggregations (total claims, avg amount, denial rate)
- `mart_denial_analysis`: Denial patterns by payer, provider, diagnosis
- `mart_utilization_metrics`: Bed utilization, length of stay, readmission indicators

## Orchestration

### Airflow DAGs

Two DAGs manage the pipeline:

1. **healthcare_pipeline** (daily at 06:00 UTC)
   - 6 TaskGroups: ingestion → bronze → silver → gold → dbt → quality
   - Sequential execution with error handling and retry logic
   - `max_active_runs=1` prevents concurrent pipeline executions

2. **data_quality_monitoring** (every 6 hours)
   - Runs Bronze, Silver, Gold validations in parallel
   - Generates JSON quality report in `data/quality/`
   - End task uses `trigger_rule="all_done"` for guaranteed report generation

### Docker Infrastructure

Airflow runs via Docker Compose with:
- PostgreSQL 15 (metadata database, port 5433)
- Airflow webserver (port 8080)
- Airflow scheduler
- One-shot init container (DB migration + admin user creation)
- Project code mounted at `/opt/airflow/project`

## Quality Framework

### Expectation Suites

Quality checks are defined in code (`src/quality/expectations.py`) as `Expectation` dataclasses:

```python
@dataclass
class Expectation:
    table: str
    check: str
    column: str | None = None
    kwargs: dict | None = None
    severity: str = "critical"  # critical, warning, info
```

### Validation Engine

The validator (`src/quality/validate.py`) uses DuckDB to execute checks:
- Connects to the relevant layer's parquet/Delta files
- Runs each expectation and collects pass/fail results
- Reports summary with severity levels
- CLI interface: `python -m src.quality.validate --layer bronze|silver|gold`

## Security Considerations

- All data is synthetic — no real PHI/PII is ever stored or processed
- PHI masking at Silver layer uses irreversible SHA-256 hashing
- No credentials stored in code (environment variables via `.env`)
- Bandit security scanning in pre-commit hooks
- `.gitignore` excludes sensitive files (`.env`, `*.duckdb`, Delta logs)
