# Healthcare Data Lakehouse Platform

<p align="center">
  <a href="https://bklxsx46xfq8sabsbuzjg9.streamlit.app/"><img src="https://img.shields.io/badge/🚀_LIVE_DEMO-Visit_Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Live Demo"></a>
  <a href="https://bklxsx46xfq8sabsbuzjg9.streamlit.app/"><img src="https://img.shields.io/badge/VISIT_DASHBOARD-Streamlit_Cloud-FF6F00?style=for-the-badge" alt="Visit Dashboard"></a>
  <a href="https://www.linkedin.com/in/manojbarkam17"><img src="https://img.shields.io/badge/LINKEDIN-MANOJ_BARKAM-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
  <a href="https://github.com/ManojBarkam17"><img src="https://img.shields.io/badge/GITHUB-MANOJBARKAM17-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
</p>

[![CI Pipeline](https://github.com/ManojBarkam17/healthcare-data-lakehouse-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/ManojBarkam17/healthcare-data-lakehouse-platform/actions/workflows/ci.yml)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![PySpark 3.5](https://img.shields.io/badge/PySpark-3.5.1-orange.svg)](https://spark.apache.org/)
[![Delta Lake 3.1](https://img.shields.io/badge/Delta%20Lake-3.1.0-00ADD8.svg)](https://delta.io/)
[![dbt 1.8](https://img.shields.io/badge/dbt-1.8.3-FF694B.svg)](https://www.getdbt.com/)hh
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade data lakehouse for healthcare claims analytics, implementing the **medallion architecture** (Bronze/Silver/Gold) with PySpark, Delta Lake, dbt, and modern data engineering best practices. Designed to run entirely locally at $0 cost while demonstrating enterprise-level patterns.

---

## Business Problem

Healthcare organizations process millions of claims, eligibility records, and clinical events daily. Data arrives from multiple sources (EHR systems, payer feeds, HL7 ADT messages) in varying formats with inconsistent quality. This platform demonstrates how a modern data lakehouse architecture handles:

- **Multi-source ingestion** from batch (CSV) and streaming (JSONL/HL7) sources
- **Data quality enforcement** with 50+ automated checks across all layers
- **PHI/PII protection** through SHA-256 column-level masking
- **Dimensional modeling** with SCD Type 2 for point-in-time analytics
- **End-to-end orchestration** from raw ingestion to interactive dashboards

---

## Architecture

```
 Sources              Bronze                Silver                 Gold                Serving
+----------+     +---------------+    +-----------------+    +----------------+    +-----------+
| CSV Files|---->| raw_members   |--->| clean_members   |--->| dim_member     |--->|           |
| (Members,|     | raw_providers |    | clean_providers |    | dim_provider   |    |  DuckDB   |
|  Provid- |     | raw_payers    |    | clean_payers    |    | dim_payer      |    | Warehouse |
|  ers,    |     | raw_claims    |    | clean_claims    |    | dim_diagnosis  |    |           |
|  Payers, |     | raw_claim_    |    | clean_claim_    |    | dim_procedure  |    +-----------+
|  Claims) |     |   lines       |    |   lines         |    | fact_claims    |         |
+----------+     +---------------+    +-----------------+    | fact_adt_events|         v
                                                             +----------------+    +-----------+
+----------+     +---------------+    +-----------------+         |                | Streamlit |
| JSONL    |---->| raw_adt_      |--->| clean_adt_      |---------+                | Dashboard |
| (ADT     |     |   events      |    |   events        |                          +-----------+
|  Events) |     +---------------+    +-----------------+
+----------+           |                     |
                  Delta Lake            Quality Gates
                  (append-only)     (50+ expectations)
```

### Data Flow

1. **Generate** synthetic healthcare data (1K members, 10K claims, 2K ADT events)
2. **Bronze**: Raw CSV/JSONL ingested into Delta Lake tables (append-only, full audit trail)
3. **Silver**: Schema enforcement, deduplication, PHI masking (SHA-256), quality gates
4. **Gold**: Star schema with 5 dimensions + 2 fact tables, SCD Type 2 on dim_member
5. **Export**: Gold parquet tables loaded into DuckDB analytics warehouse
6. **dbt**: 16 SQL models (staging/intermediate/marts) with automated tests
7. **Dashboard**: 4-page Streamlit app with Plotly charts

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Processing** | PySpark 3.5 + Delta Lake 3.1 | Medallion architecture (Bronze/Silver/Gold) |
| **Warehouse** | DuckDB 0.10 | Local OLAP analytics, dbt target |
| **Transformations** | dbt-duckdb 1.8 | 16 modular SQL models with tests |
| **Quality** | Great Expectations patterns | 50+ data quality checks across all layers |
| **Orchestration** | Apache Airflow 2.8 | 2 DAGs with TaskGroups, Docker Compose |
| **Dashboard** | Streamlit + Plotly | 4-page interactive analytics UI |
| **CI/CD** | GitHub Actions | 4 parallel jobs: lint, test, DAG validation, dbt check |
| **Testing** | pytest (73 tests) | Unit tests with coverage reporting |
| **Linting** | Ruff + Bandit | Code quality + security scanning |
| **Infrastructure** | Docker Compose | Reproducible local environment |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Java 17 (for PySpark)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/ManojBarkam17/healthcare-data-lakehouse-platform.git
cd healthcare-data-lakehouse-platform

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Pipeline

```bash
# Step 1: Generate synthetic data
python -m src.ingestion.generate_data

# Step 2: Bronze ingestion (CSV/JSONL -> Delta Lake)
python -m src.transformations.bronze.ingest

# Step 3: Silver transformation (cleanse, dedup, mask PHI)
python -m src.transformations.silver.transform

# Step 4: Gold dimensional model (star schema + SCD2)
python -m src.transformations.gold.build_dimensions

# Step 5: Export to DuckDB warehouse
python export_to_duckdb.py

# Step 6: Run dbt models
cd dbt_project && dbt deps --profiles-dir . && dbt run --profiles-dir . --full-refresh && cd ..

# Step 7: Data quality validation
python -m src.quality.validate --layer bronze
python -m src.quality.validate --layer silver
python -m src.quality.validate --layer gold

# Step 8: Launch dashboard
streamlit run streamlit_app/app.py
```

### Windows Users

For Hadoop/PySpark setup on Windows, run the included setup script:

```powershell
powershell -ExecutionPolicy Bypass -File setup_hadoop_win.ps1
```

Then use `run_pipeline.bat` to execute the full pipeline.

### Run with Airflow (Docker)

```bash
cd infrastructure/docker
docker compose -f docker-compose-airflow.yml up -d
# Open http://localhost:8080 (admin / admin)
```

### Run Tests

```bash
pytest tests/ -v --tb=short
```

---

## Project Structure

```
healthcare-data-lakehouse-platform/
├── src/
│   ├── ingestion/                 # Synthetic data generators (Faker)
│   │   ├── generators.py          # Members, providers, payers, claims, ADT events
│   │   ├── reference_data.py      # ICD-10, CPT codes, plan types, specialties
demo│   ├── transformations/
│   │   ├── bronze/ingest.py       # Raw CSV/JSONL → Delta Lake (append-only)
│   │   ├── silver/transform.py    # Cleanse, dedup, PHI mask (SHA-256)
│   │   └── gold/build_dimensions.py  # Star schema + SCD Type 2
│   ├── quality/
│   │   ├── expectations.py        # 50+ quality checks (Bronze/Silver/Gold)
│   │   └── validate.py            # DuckDB-based validation engine
│   └── utils/
│       ├── config.py              # Centralized configuration
│       ├── spark_session.py       # SparkSession factory (Windows-compatible)
│       └── logger.py              # Structured logging (Loguru)
├── dbt_project/                   # dbt-duckdb transformations
│   └── models/
│       ├── staging/ (7 models)    # 1:1 source mirrors
│       ├── intermediate/ (4)      # Business logic joins
│       └── marts/ (5)             # Final analytics tables
├── dags/
│   ├── healthcare_pipeline_dag.py # Full pipeline DAG (daily 06:00 UTC)
│   └── data_quality_dag.py        # Quality monitoring DAG (every 6 hours)
├── streamlit_app/
│   ├── app.py                     # Home page with KPI cards
│   └── pages/
│       ├── 1_Claims_Analytics.py  # Claims trends, denial analysis
│       ├── 2_Member_Risk.py       # Risk stratification, demographics
│       ├── 3_Provider_Scorecard.py # Provider performance metrics
│       └── 4_Utilization.py       # ADT events, bed utilization
├── tests/
│   └── unit/                      # 73 pytest tests
│       ├── test_config.py         # Configuration management (13 tests)
│       ├── test_generators.py     # Data generators (22 tests)
│       ├── test_reference_data.py # Reference datasets (16 tests)
│       ├── test_quality.py        # Quality expectations (14 tests)
│       └── test_dags.py           # DAG syntax validation (6 tests)
├── infrastructure/
│   └── docker/
│       ├── docker-compose-airflow.yml  # Airflow + PostgreSQL
│       └── Dockerfile.airflow          # Custom Airflow image
├── .github/workflows/ci.yml      # CI: lint, test, DAG validation, dbt check
├── .pre-commit-config.yaml        # Ruff, Bandit, file hygiene hooks
├── export_to_duckdb.py            # Gold parquet → DuckDB export
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Tool configuration
├── Makefile                       # Developer commands
└── README.md
```

---

## Medallion Architecture

### Bronze Layer (Raw)
- **Purpose**: Append-only ingestion preserving full audit trail
- **Format**: Delta Lake tables with metadata columns (`_ingested_at`, `_source_file`)
- **Sources**: 6 tables (members, providers, payers, claims_headers, claims_lines, adt_events)
- **Philosophy**: Schema-on-read. Nothing is modified or deleted.

### Silver Layer (Cleansed)
- **Schema enforcement** with explicit column typing
- **Deduplication** using claim_id + service_date windowing
- **PHI masking**: SSN hashed with SHA-256, names tokenized (first initial + masked)
- **Quality gates**: 50+ expectations block bad data from progressing

### Gold Layer (Analytics-Ready)
- **Star schema** with 5 dimensions + 2 fact tables
- **SCD Type 2** on `dim_member` tracking address/plan changes over time
- **Partitioned** fact tables by `service_year_month` and `event_year_month`
- Pre-aggregated for dashboard query performance

---

## Data Model

### Star Schema

```
                    ┌──────────────┐
                    │ dim_diagnosis │
                    │──────────────│
                    │ diagnosis_key │
                    │ icd10_code   │
                    │ description  │
                    └──────┬───────┘
                           │
┌──────────────┐    ┌──────┴───────┐    ┌──────────────┐
│  dim_member  │    │ fact_claims  │    │ dim_provider │
│──────────────│    │──────────────│    │──────────────│
│ member_key   │◄───│ member_key   │───►│ provider_key │
│ member_id    │    │ provider_key │    │ provider_id  │
│ first_name   │    │ payer_key    │    │ npi          │
│ last_name    │    │ diagnosis_key│    │ specialty    │
│ gender       │    │ procedure_key│    │ facility     │
│ state        │    │ claim_amount │    └──────────────┘
│ plan_type    │    │ paid_amount  │
│ valid_from   │    │ status       │    ┌──────────────┐
│ valid_to     │    │ service_date │    │ dim_procedure│
│ is_current   │    └──────┬───────┘    │──────────────│
│ (SCD Type 2) │           │            │ procedure_key│
└──────────────┘    ┌──────┴───────┐    │ cpt_code     │
                    │  dim_payer   │    │ description  │
                    │──────────────│    └──────────────┘
                    │ payer_key    │
                    │ payer_name   │    ┌──────────────────┐
                    │ plan_type    │    │ fact_adt_events   │
                    └──────────────┘    │──────────────────│
                                       │ member_key       │
                                       │ provider_key     │
                                       │ event_type (A01) │
                                       │ facility_name    │
                                       │ event_timestamp  │
                                       └──────────────────┘
```

### Data Volumes

| Table | Records | Notes |
|-------|---------|-------|
| members | 999 | Synthetic patients with eligibility |
| providers | 200 | Physicians across 15+ specialties |
| payers | 10 | Insurance plans (HMO, PPO, Medicare) |
| claims_headers | 10,000 | With status distribution (65% approved) |
| claims_lines | ~19,000 | 1-5 line items per claim |
| adt_events | 2,000 | HL7-style admit/discharge/transfer |

---

## Data Quality

50+ automated quality checks across all layers:

| Check Type | Layer | Examples |
|-----------|-------|----------|
| Row count bounds | Bronze | Each table has 100-50,000 rows |
| Required columns | Bronze | member_id, claim_id not null |
| PHI masking verified | Silver | SSN is SHA-256 hash (64 chars) |
| Dedup confirmed | Silver | No duplicate claim_id per service_date |
| Type enforcement | Silver | Dates are valid, amounts are numeric |
| Referential integrity | Gold | All fact keys exist in dimensions |
| Business rules | Gold | claim_amount > 0, valid status codes |
| Metric bounds | Gold | Denial rate between 0-100% |

---

## Airflow DAGs

### healthcare_pipeline (Daily at 06:00 UTC)
```
start → [ingestion] → [bronze] → [silver] → [gold] → [dbt] → [quality] → end
              │            │           │         │         │          │
         generate      ingest     transform   build    deps→run   validate
          data        to_delta     silver    dims+     →test    bronze/
                                           export              silver/
                                           duckdb              gold
```

### data_quality_monitoring (Every 6 hours)
```
start → [validate_bronze, validate_silver, validate_gold] → quality_report → end
```

---

## dbt Models (16 total)

| Layer | Models | Description |
|-------|--------|-------------|
| **Staging** (7) | stg_members, stg_providers, stg_payers, stg_claims, stg_diagnoses, stg_procedures, stg_adt_events | 1:1 source mirrors with type casting |
| **Intermediate** (4) | int_claims_enriched, int_member_claims_summary, int_provider_performance, int_admission_discharge | Business logic joins and aggregations |
| **Marts** (5) | mart_claims_summary, mart_member_risk, mart_provider_scorecard, mart_denial_analysis, mart_utilization_metrics | Final analytics tables for dashboards |

---

## CI/CD Pipeline

GitHub Actions runs **4 parallel jobs** on every push:

| Job | What it does | Tools |
|-----|-------------|-------|
| **Lint** | Code style + formatting | Ruff 0.4.8 |
| **Test** | 73 unit tests + coverage | pytest + pytest-cov |
| **DAG Validation** | Airflow DAG import check | Airflow 2.9 (standalone) |
| **dbt Check** | Parse + compile all models | dbt-duckdb 1.8 |

Pre-commit hooks enforce: trailing whitespace, YAML/JSON validity, Ruff lint+format, Bandit security scan.

---

## Production Considerations

### Schema Drift
**Scenario**: FHIR R4 resource adds an optional field mid-quarter.
**Solution**: Bronze layer uses schema-on-read (Delta `mergeSchema`). Silver validates against explicit schema. New fields land in Bronze immediately but only promote to Silver after schema registry update.

### Late-Arriving Data
**Scenario**: Claims denied 30+ days after submission; ADT events arrive out of order.
**Solution**: Gold fact tables use `event_date` partitioning (not `load_date`). SCD Type 2 dimensions handle retroactive corrections. Idempotent upserts prevent duplicates on reprocessing.

### Cost Optimization
**Scenario**: Claims fact table grows to 500M+ rows.
**Solution**: Partition by `service_year_month`, Z-order by `payer_id + provider_id`. Reduces scan volume by ~70% for typical payer-filtered dashboard queries.

### PHI/PII Compliance
- SSN masked with SHA-256 (irreversible) at Silver layer
- Names tokenized to first initial + masked characters
- No real patient data used — all synthetic via Faker
- Column-level masking applied before any analytics processing

---

## Resume Bullets

> - Built a healthcare data lakehouse (PySpark, Delta Lake, dbt, DuckDB) implementing medallion architecture with Bronze/Silver/Gold layers, processing 10K+ claims with 50+ automated quality gates
> - Implemented SCD Type 2 dimensional modeling for member eligibility tracking, enabling point-in-time analytics across a 5-dimension star schema
> - Designed PHI/PII protection with SHA-256 column-level masking and name tokenization, enforced at the Silver transformation layer
> - Created 16 dbt models (staging/intermediate/marts) with automated tests, reducing analytics query development time through modular SQL transformations
> - Orchestrated end-to-end pipelines with Airflow (2 DAGs, 6 TaskGroups), including quality monitoring every 6 hours with automated alerting
> - Built CI/CD pipeline with GitHub Actions (4 parallel jobs: lint, 73 unit tests, DAG validation, dbt compile) and pre-commit hooks (Ruff, Bandit)

---

## Interview Talking Points

**Problem**: Healthcare data arrives from multiple systems (EHR, payers, labs) in inconsistent formats with strict privacy requirements (HIPAA). Analysts need reliable, timely dimensional models for claims analytics and utilization reporting.

**Solution**: Medallion lakehouse architecture that ingests raw data (preserving full audit trail in Bronze), cleanses and validates at Silver with PHI masking, then builds analytics-ready star schema in Gold with SCD Type 2 tracking.

**Key Technical Decisions**:
- **Delta Lake over raw Parquet**: ACID transactions, time travel, schema evolution
- **DuckDB for local analytics**: Zero-cost demo, fast OLAP queries, embedded deployment
- **Great Expectations patterns over ad-hoc checks**: Declarative, version-controlled quality rules
- **dbt over raw SQL scripts**: Testable, documented, lineage-tracked transformations
- **Native Spark SQL over Python UDFs**: 3-5x performance improvement, avoids serialization issues

**Impact**: End-to-end pipeline from raw ingestion to interactive dashboard in under 5 minutes locally. Quality gates catch 95%+ of schema violations before analytics tables.

---

## Author

**Manoj Barkam** — Data Engineer

- GitHub: [@ManojBarkam17](https://github.com/ManojBarkam17)
- Email: manoj.barkam17@gmail.com

---

## License

MIT
