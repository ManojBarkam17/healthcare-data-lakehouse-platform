# Data Governance & Compliance

## Overview

This document describes the data governance policies implemented in the Healthcare Data Lakehouse Platform, including PHI/PII handling, data lineage, access controls, and audit capabilities.

## PHI/PII Protection

### Policy

All Protected Health Information (PHI) and Personally Identifiable Information (PII) is masked at the Silver layer before any analytics processing occurs. The Bronze layer retains raw data for audit purposes but is access-restricted in production environments.

### Masking Methods

| Field | Method | Reversible | Example |
|-------|--------|-----------|---------|
| SSN | SHA-256 hash | No | `123-45-6789` → `a1b2c3...` (64 chars) |
| First Name | First char + mask | No | `John` → `J***` |
| Last Name | First char + mask | No | `Smith` → `S****` |
| Date of Birth | Preserved | N/A | Required for age-based analytics |
| Address | Preserved at state level | N/A | Full address dropped at Gold |
| Phone | Not promoted to Gold | N/A | Exists only in Bronze/Silver |
| Email | Not promoted to Gold | N/A | Exists only in Bronze/Silver |

### Implementation

PHI masking uses native Spark SQL functions (not Python UDFs) for performance:

```python
# SSN: Irreversible SHA-256 hash
masked_ssn = F.sha2(F.col("ssn"), 256)

# Names: First character preserved, remainder masked
masked_name = F.concat(
    F.substring(F.col("first_name"), 1, 1),
    F.expr("repeat('*', length(first_name) - 1)")
)
```

### Why Native Spark SQL?

Python UDFs serialize data between JVM and Python processes, causing:
- 3-5x performance degradation
- `PicklingError` on Windows when using complex UDFs
- Loss of Spark's query optimization (Catalyst)

Native Spark SQL functions run entirely in the JVM, avoiding all these issues.

## Data Lineage

### Column-Level Lineage

```
Bronze                    Silver                   Gold
───────────────────────────────────────────────────────────
raw_members.ssn      →  clean_members.ssn_hash  →  dim_member.ssn_hash
raw_members.first_name → clean_members.first_name → dim_member.first_name (masked)
raw_claims.claim_id  →  clean_claims.claim_id   →  fact_claims.claim_id
raw_claims.charge_amt → clean_claims.charge_amt  → fact_claims.claim_amount
```

### Table-Level Lineage

```
                    dbt Lineage Graph
                    ─────────────────
Sources (Gold DuckDB tables)
    │
    ├── stg_members ──────┐
    ├── stg_providers ────┤
    ├── stg_payers ───────┤
    ├── stg_claims ───────┼── int_claims_enriched ──┬── mart_claims_summary
    ├── stg_diagnoses ────┤                         ├── mart_denial_analysis
    └── stg_procedures ───┘                         │
                                                    │
    stg_members ──── int_member_claims_summary ─────┴── mart_member_risk
    stg_providers ── int_provider_performance ──────── mart_provider_scorecard
    stg_adt_events ─ int_admission_discharge ──────── mart_utilization_metrics
```

## Data Quality Governance

### Quality Tiers

| Severity | Action | Example |
|----------|--------|---------|
| **Critical** | Block pipeline, alert on-call | Null member_id in claims |
| **Warning** | Log and continue, alert team | Denial rate > 30% |
| **Info** | Log only | New ICD-10 code not in reference |

### Quality SLAs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Schema conformance | 100% | All Silver records match expected schema |
| Null rate (key columns) | < 1% | member_id, claim_id, provider_id |
| Duplicate rate | 0% | Post-dedup in Silver layer |
| Referential integrity | 100% | All fact foreign keys exist in dimensions |
| Data freshness | < 24 hours | Bronze ingestion timestamp vs current time |

### Quality Monitoring

- **Automated**: Data quality DAG runs every 6 hours
- **Reports**: JSON quality reports stored in `data/quality/`
- **Alerting**: Configurable via Airflow connections (email, Slack)

## Access Control Model (Production Reference)

In a production deployment, the following access model would apply:

| Role | Bronze | Silver | Gold | Dashboard |
|------|--------|--------|------|-----------|
| Data Engineer | Read/Write | Read/Write | Read/Write | View |
| Data Analyst | No Access | Read Only | Read/Write | View/Edit |
| Business User | No Access | No Access | Read Only | View |
| Compliance Officer | Read Only | Read Only | Read Only | View |

### Key Principles

1. **Least privilege**: Each role gets minimum required access
2. **Bronze is restricted**: Contains unmasked PHI — limited to engineers + compliance
3. **Gold is analytics-safe**: All PHI masked, safe for analyst access
4. **Audit trail**: All data operations logged with timestamps and user context

## Audit Capabilities

### Bronze Layer Audit Trail

Every record in Bronze includes:
- `_ingested_at`: Timestamp of ingestion
- `_source_file`: Original source file name
- Delta Lake transaction log: Full history of all operations

### Delta Lake Time Travel

Bronze tables support time travel queries (production feature):

```sql
-- Query data as it existed at a specific point
SELECT * FROM delta.`data/bronze/raw_members` VERSION AS OF 5;

-- View all changes to a table
DESCRIBE HISTORY delta.`data/bronze/raw_members`;
```

## Regulatory Compliance Notes

This platform demonstrates patterns relevant to:

- **HIPAA**: PHI masking, access controls, audit trails
- **HITECH**: Breach notification preparedness (know where PHI exists)
- **CMS Interoperability**: FHIR-compatible data structures

Note: This is a demonstration platform using 100% synthetic data. No real patient data is stored or processed.

## Data Retention Policy (Production Reference)

| Layer | Retention | Rationale |
|-------|-----------|-----------|
| Bronze | 7 years | Regulatory requirement, full audit trail |
| Silver | 3 years | Operational analytics window |
| Gold | Rolling 3 years | Dashboard performance optimization |
| Quality Reports | 1 year | Trend analysis and compliance |
