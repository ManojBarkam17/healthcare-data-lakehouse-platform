-- =============================================================================
-- Snowflake Setup — Healthcare Data Lakehouse
-- =============================================================================
-- Creates the database, schemas (medallion layers), warehouses, and roles.
-- Run this as SYSADMIN or equivalent.
--
-- NOTE: This is a reference implementation. The runnable demo uses
--       PySpark + DuckDB locally. These scripts demonstrate Snowflake
--       competency for production migration.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Database
-- ---------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS HEALTHCARE_LAKEHOUSE
    COMMENT = 'Healthcare data lakehouse with medallion architecture';

USE DATABASE HEALTHCARE_LAKEHOUSE;

-- ---------------------------------------------------------------------------
-- Schemas (one per medallion layer)
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS BRONZE
    COMMENT = 'Raw ingested data — append-only, full audit trail';

CREATE SCHEMA IF NOT EXISTS SILVER
    COMMENT = 'Cleansed data — deduplicated, PHI masked, quality validated';

CREATE SCHEMA IF NOT EXISTS GOLD
    COMMENT = 'Analytics-ready — star schema dimensions and facts';

CREATE SCHEMA IF NOT EXISTS STAGING
    COMMENT = 'Temporary landing zone for file ingestion';

-- ---------------------------------------------------------------------------
-- Virtual Warehouses
-- ---------------------------------------------------------------------------
CREATE WAREHOUSE IF NOT EXISTS HEALTHCARE_INGEST_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    COMMENT = 'Ingestion workloads (Bronze layer)';

CREATE WAREHOUSE IF NOT EXISTS HEALTHCARE_TRANSFORM_WH
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 120
    AUTO_RESUME = TRUE
    COMMENT = 'Transformation workloads (Silver/Gold layers)';

CREATE WAREHOUSE IF NOT EXISTS HEALTHCARE_ANALYTICS_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    COMMENT = 'Dashboard and analyst queries';

-- ---------------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------------
CREATE ROLE IF NOT EXISTS HEALTHCARE_ENGINEER;
CREATE ROLE IF NOT EXISTS HEALTHCARE_ANALYST;
CREATE ROLE IF NOT EXISTS HEALTHCARE_VIEWER;

-- Engineer: full access to all schemas
GRANT USAGE ON DATABASE HEALTHCARE_LAKEHOUSE TO ROLE HEALTHCARE_ENGINEER;
GRANT ALL ON SCHEMA BRONZE TO ROLE HEALTHCARE_ENGINEER;
GRANT ALL ON SCHEMA SILVER TO ROLE HEALTHCARE_ENGINEER;
GRANT ALL ON SCHEMA GOLD TO ROLE HEALTHCARE_ENGINEER;
GRANT ALL ON SCHEMA STAGING TO ROLE HEALTHCARE_ENGINEER;
GRANT USAGE ON WAREHOUSE HEALTHCARE_INGEST_WH TO ROLE HEALTHCARE_ENGINEER;
GRANT USAGE ON WAREHOUSE HEALTHCARE_TRANSFORM_WH TO ROLE HEALTHCARE_ENGINEER;

-- Analyst: read Silver + Gold, no Bronze (contains unmasked PHI)
GRANT USAGE ON DATABASE HEALTHCARE_LAKEHOUSE TO ROLE HEALTHCARE_ANALYST;
GRANT USAGE ON SCHEMA SILVER TO ROLE HEALTHCARE_ANALYST;
GRANT SELECT ON ALL TABLES IN SCHEMA SILVER TO ROLE HEALTHCARE_ANALYST;
GRANT USAGE ON SCHEMA GOLD TO ROLE HEALTHCARE_ANALYST;
GRANT SELECT ON ALL TABLES IN SCHEMA GOLD TO ROLE HEALTHCARE_ANALYST;
GRANT USAGE ON WAREHOUSE HEALTHCARE_ANALYTICS_WH TO ROLE HEALTHCARE_ANALYST;

-- Viewer: Gold only (all PHI is masked)
GRANT USAGE ON DATABASE HEALTHCARE_LAKEHOUSE TO ROLE HEALTHCARE_VIEWER;
GRANT USAGE ON SCHEMA GOLD TO ROLE HEALTHCARE_VIEWER;
GRANT SELECT ON ALL TABLES IN SCHEMA GOLD TO ROLE HEALTHCARE_VIEWER;
GRANT USAGE ON WAREHOUSE HEALTHCARE_ANALYTICS_WH TO ROLE HEALTHCARE_VIEWER;
