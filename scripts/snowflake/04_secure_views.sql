-- =============================================================================
-- Snowflake Secure Views — Healthcare Data Lakehouse
-- =============================================================================
-- Secure views prevent users from seeing the underlying SQL logic,
-- which could expose masking implementation details.
-- These views provide analyst-friendly access to Gold layer data.
-- =============================================================================

USE DATABASE HEALTHCARE_LAKEHOUSE;
USE SCHEMA GOLD;

-- ---------------------------------------------------------------------------
-- Claims Summary View
-- Provides pre-aggregated claims metrics by payer and month
-- ---------------------------------------------------------------------------
CREATE OR REPLACE SECURE VIEW GOLD.VW_CLAIMS_SUMMARY AS
SELECT
    fc.service_year_month,
    dp.payer_name,
    dp.payer_type,
    COUNT(*)                                    AS total_claims,
    SUM(CASE WHEN fc.status = 'approved' THEN 1 ELSE 0 END)
                                                AS approved_claims,
    SUM(CASE WHEN fc.status = 'denied' THEN 1 ELSE 0 END)
                                                AS denied_claims,
    ROUND(AVG(fc.claim_amount), 2)              AS avg_claim_amount,
    ROUND(SUM(fc.claim_amount), 2)              AS total_charged,
    ROUND(SUM(fc.paid_amount), 2)               AS total_paid,
    ROUND(
        SUM(CASE WHEN fc.status = 'denied' THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                           AS denial_rate_pct
FROM GOLD.FACT_CLAIMS fc
LEFT JOIN GOLD.DIM_PAYER dp ON fc.payer_key = dp.payer_key
GROUP BY fc.service_year_month, dp.payer_name, dp.payer_type
ORDER BY fc.service_year_month DESC, total_claims DESC
COMMENT = 'Claims summary by payer and month — for analyst dashboards';

-- ---------------------------------------------------------------------------
-- Member Risk View
-- Identifies high-risk members based on claims patterns
-- ---------------------------------------------------------------------------
CREATE OR REPLACE SECURE VIEW GOLD.VW_MEMBER_RISK AS
SELECT
    dm.member_id,
    dm.gender,
    dm.state,
    dm.plan_type,
    DATEDIFF('year', dm.date_of_birth, CURRENT_DATE()) AS age,
    COUNT(fc.claim_id)                          AS total_claims,
    ROUND(SUM(fc.claim_amount), 2)              AS total_charged,
    ROUND(AVG(fc.claim_amount), 2)              AS avg_claim_amount,
    SUM(CASE WHEN fc.status = 'denied' THEN 1 ELSE 0 END)
                                                AS denied_claims,
    COUNT(DISTINCT dd.icd10_code)               AS distinct_diagnoses,
    CASE
        WHEN COUNT(fc.claim_id) > 20 THEN 'High'
        WHEN COUNT(fc.claim_id) > 10 THEN 'Medium'
        ELSE 'Low'
    END                                         AS risk_tier
FROM GOLD.DIM_MEMBER dm
LEFT JOIN GOLD.FACT_CLAIMS fc ON dm.member_key = fc.member_key
LEFT JOIN GOLD.DIM_DIAGNOSIS dd ON fc.diagnosis_key = dd.diagnosis_key
WHERE dm.is_current = TRUE
GROUP BY dm.member_id, dm.gender, dm.state, dm.plan_type, dm.date_of_birth
COMMENT = 'Member risk stratification — for care management';

-- ---------------------------------------------------------------------------
-- Provider Scorecard View
-- ---------------------------------------------------------------------------
CREATE OR REPLACE SECURE VIEW GOLD.VW_PROVIDER_SCORECARD AS
SELECT
    dprov.provider_id,
    dprov.npi,
    dprov.first_name || ' ' || dprov.last_name  AS provider_name,
    dprov.specialty,
    dprov.facility_name,
    COUNT(fc.claim_id)                          AS total_claims,
    COUNT(DISTINCT fc.member_key)               AS unique_patients,
    ROUND(AVG(fc.claim_amount), 2)              AS avg_claim_amount,
    ROUND(SUM(fc.paid_amount), 2)               AS total_paid,
    ROUND(
        SUM(CASE WHEN fc.status = 'denied' THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                           AS denial_rate_pct
FROM GOLD.DIM_PROVIDER dprov
LEFT JOIN GOLD.FACT_CLAIMS fc ON dprov.provider_key = fc.provider_key
GROUP BY dprov.provider_id, dprov.npi, dprov.first_name, dprov.last_name,
         dprov.specialty, dprov.facility_name
COMMENT = 'Provider performance metrics — for network management';

-- ---------------------------------------------------------------------------
-- ADT Utilization View
-- ---------------------------------------------------------------------------
CREATE OR REPLACE SECURE VIEW GOLD.VW_ADT_UTILIZATION AS
SELECT
    event_year_month,
    event_type,
    event_description,
    facility_name,
    department,
    COUNT(*)                                    AS event_count,
    COUNT(DISTINCT member_key)                  AS unique_patients
FROM GOLD.FACT_ADT_EVENTS
GROUP BY event_year_month, event_type, event_description,
         facility_name, department
ORDER BY event_year_month DESC, event_count DESC
COMMENT = 'ADT event utilization — for capacity planning';

-- ---------------------------------------------------------------------------
-- Grant views to analyst role
-- ---------------------------------------------------------------------------
GRANT SELECT ON ALL VIEWS IN SCHEMA GOLD TO ROLE HEALTHCARE_ANALYST;
GRANT SELECT ON ALL VIEWS IN SCHEMA GOLD TO ROLE HEALTHCARE_VIEWER;
