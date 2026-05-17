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

*Updated as phases progress.*
