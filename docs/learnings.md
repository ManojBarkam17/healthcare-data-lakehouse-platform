# Engineering Decisions & Learnings

## Phase 1: Project Setup

**Decision: DuckDB as local warehouse instead of Snowflake**
- Rationale: Enables $0 runnable demo. DuckDB handles OLAP queries efficiently for demo-scale data (100K claims). Snowflake DDL is provided as migration-ready reference scripts.
- Trade-off: Lose Snowflake-specific features (clustering, secure views) in live demo, but gain zero-cost reproducibility.

**Decision: Monorepo structure**
- Rationale: For a portfolio project, a single repo with clear folder boundaries is easier to navigate than multiple repos. Recruiters/interviewers can `git clone` once and see everything.
- Trade-off: Slightly larger clone, but `data/` artifacts are gitignored.

**Decision: Two demo modes (full vs. light)**
- Rationale: Not everyone has 16GB RAM or Docker. The light mode runs the core medallion pipeline without Kafka/Airflow overhead, making it accessible on any developer laptop.

---

## Phase 2: Synthetic Data Generation

**Decision: Faker + custom generators over Synthea**
- Rationale: Synthea generates FHIR bundles which would need parsing. Faker + custom generators produce flat CSV/JSONL that directly mirrors real eligibility files and claims feeds. Faster to build, easier to control volume.
- Trade-off: Less clinically realistic than Synthea, but sufficient for demonstrating pipeline patterns.

**Decision: Seeded randomness (seed=42)**
- Rationale: Reproducible data across runs. Same seed → same members/claims → consistent screenshots and demo behavior.

---

## Phase 3-5: Bronze / Silver / Gold Pipeline

**Decision: SHA-256 for PHI masking instead of tokenization service**
- Rationale: Demonstrates the masking pattern without external dependencies. In production, you'd use a key vault or dedicated tokenization service (e.g., Protegrity, Voltage).
- Trade-off: SHA-256 is a one-way hash — can't unmask. Production would need reversible tokenization for authorized users.

**Decision: Overwrite mode in Silver/Gold instead of incremental MERGE**
- Rationale: For demo-scale data (10K-100K records), full rebuild is simpler and faster than incremental upserts. The MERGE pattern is documented in comments for interview discussion.
- Trade-off: Not production-efficient at scale, but demonstrates the right schema and transformations.

**Decision: SCD Type 2 on dim_member with effective_start/end/is_current**
- Rationale: This is the most-asked dimensional modeling interview question. Tracking plan_type and address changes shows real-world applicability for eligibility analytics.

**Decision: Export Gold to DuckDB**
- Rationale: Bridges the Spark-based pipeline with dbt-duckdb and Streamlit. DuckDB acts as the "warehouse" layer that Snowflake would fill in production.

---

*Updated as phases progress.*
