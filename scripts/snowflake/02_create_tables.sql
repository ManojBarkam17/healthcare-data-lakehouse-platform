-- =============================================================================
-- Snowflake Table DDL — Healthcare Data Lakehouse
-- =============================================================================
-- Creates Bronze, Silver, and Gold tables with appropriate clustering,
-- partitioning, and constraints.
-- =============================================================================

USE DATABASE HEALTHCARE_LAKEHOUSE;

-- =========================================================================
-- BRONZE LAYER — Raw ingested data
-- =========================================================================

CREATE OR REPLACE TABLE BRONZE.RAW_MEMBERS (
    member_id       VARCHAR(20)     NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    date_of_birth   VARCHAR(20),
    gender          VARCHAR(1),
    ssn             VARCHAR(11),
    address         VARCHAR(200),
    city            VARCHAR(100),
    state           VARCHAR(2),
    zip_code        VARCHAR(10),
    phone           VARCHAR(20),
    email           VARCHAR(100),
    plan_type       VARCHAR(20),
    payer_id        VARCHAR(20),
    effective_date  VARCHAR(20),
    termination_date VARCHAR(20),
    created_at      VARCHAR(30),
    -- Ingestion metadata
    _ingested_at    TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    _source_file    VARCHAR(200),
    _batch_id       VARCHAR(50)
)
CLUSTER BY (member_id)
COMMENT = 'Raw member data — append-only, contains unmasked PHI';

CREATE OR REPLACE TABLE BRONZE.RAW_PROVIDERS (
    provider_id     VARCHAR(50)     NOT NULL,
    npi             VARCHAR(10),
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    specialty       VARCHAR(100),
    facility_name   VARCHAR(200),
    address         VARCHAR(200),
    city            VARCHAR(100),
    state           VARCHAR(2),
    zip_code        VARCHAR(10),
    tax_id          VARCHAR(20),
    is_active       BOOLEAN,
    created_at      VARCHAR(30),
    _ingested_at    TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    _source_file    VARCHAR(200),
    _batch_id       VARCHAR(50)
)
COMMENT = 'Raw provider data — append-only';

CREATE OR REPLACE TABLE BRONZE.RAW_CLAIMS_HEADERS (
    claim_id        VARCHAR(50)     NOT NULL,
    member_id       VARCHAR(20),
    provider_id     VARCHAR(50),
    payer_id        VARCHAR(20),
    service_date    VARCHAR(20),
    submission_date VARCHAR(20),
    total_charge    NUMBER(12,2),
    allowed_amount  NUMBER(12,2),
    paid_amount     NUMBER(12,2),
    status          VARCHAR(30),
    denial_reason   VARCHAR(50),
    _ingested_at    TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    _source_file    VARCHAR(200),
    _batch_id       VARCHAR(50)
)
CLUSTER BY (service_date, payer_id)
COMMENT = 'Raw claim headers — append-only';

CREATE OR REPLACE TABLE BRONZE.RAW_CLAIMS_LINES (
    claim_line_id   VARCHAR(50)     NOT NULL,
    claim_id        VARCHAR(50),
    line_number     INTEGER,
    cpt_code        VARCHAR(10),
    cpt_description VARCHAR(200),
    icd10_code      VARCHAR(10),
    icd10_description VARCHAR(200),
    line_charge_amount NUMBER(12,2),
    allowed_amount  NUMBER(12,2),
    paid_amount     NUMBER(12,2),
    units           INTEGER,
    service_date    VARCHAR(20),
    _ingested_at    TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    _source_file    VARCHAR(200),
    _batch_id       VARCHAR(50)
)
COMMENT = 'Raw claim line items — append-only';

CREATE OR REPLACE TABLE BRONZE.RAW_ADT_EVENTS (
    event_id        VARCHAR(50)     NOT NULL,
    event_type      VARCHAR(10),
    event_description VARCHAR(100),
    member_id       VARIANT,        -- Nested JSON in raw
    provider_id     VARIANT,        -- Nested JSON in raw
    facility_name   VARCHAR(200),
    department      VARCHAR(100),
    room_number     VARCHAR(10),
    admit_reason    VARCHAR(200),
    event_timestamp VARCHAR(30),
    message_control_id VARCHAR(20),
    sending_facility VARCHAR(20),
    _ingested_at    TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP(),
    _source_file    VARCHAR(200),
    _batch_id       VARCHAR(50)
)
COMMENT = 'Raw HL7-style ADT events — append-only';

-- =========================================================================
-- GOLD LAYER — Star schema
-- =========================================================================

CREATE OR REPLACE TABLE GOLD.DIM_MEMBER (
    member_key      INTEGER         AUTOINCREMENT,
    member_id       VARCHAR(20)     NOT NULL,
    first_name      VARCHAR(100),   -- Masked: first initial + asterisks
    last_name       VARCHAR(100),   -- Masked: first initial + asterisks
    date_of_birth   DATE,
    gender          VARCHAR(1),
    state           VARCHAR(2),
    zip_code        VARCHAR(10),
    plan_type       VARCHAR(20),
    ssn_hash        VARCHAR(64),    -- SHA-256 hash (irreversible)
    valid_from      DATE            NOT NULL,
    valid_to        DATE            NOT NULL DEFAULT '9999-12-31',
    is_current      BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (member_key)
)
CLUSTER BY (member_id, is_current)
COMMENT = 'Member dimension — SCD Type 2 with change tracking';

CREATE OR REPLACE TABLE GOLD.DIM_PROVIDER (
    provider_key    INTEGER         AUTOINCREMENT,
    provider_id     VARCHAR(50)     NOT NULL,
    npi             VARCHAR(10),
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    specialty       VARCHAR(100),
    facility_name   VARCHAR(200),
    state           VARCHAR(2),
    is_active       BOOLEAN,
    PRIMARY KEY (provider_key)
)
COMMENT = 'Provider dimension';

CREATE OR REPLACE TABLE GOLD.DIM_PAYER (
    payer_key       INTEGER         AUTOINCREMENT,
    payer_id        VARCHAR(20)     NOT NULL,
    payer_name      VARCHAR(200),
    payer_type      VARCHAR(50),
    state           VARCHAR(2),
    is_active       BOOLEAN,
    PRIMARY KEY (payer_key)
)
COMMENT = 'Payer/insurance dimension';

CREATE OR REPLACE TABLE GOLD.DIM_DIAGNOSIS (
    diagnosis_key   INTEGER         AUTOINCREMENT,
    icd10_code      VARCHAR(10)     NOT NULL,
    description     VARCHAR(200),
    PRIMARY KEY (diagnosis_key)
)
COMMENT = 'ICD-10 diagnosis dimension';

CREATE OR REPLACE TABLE GOLD.DIM_PROCEDURE (
    procedure_key   INTEGER         AUTOINCREMENT,
    cpt_code        VARCHAR(10)     NOT NULL,
    description     VARCHAR(200),
    PRIMARY KEY (procedure_key)
)
COMMENT = 'CPT procedure dimension';

CREATE OR REPLACE TABLE GOLD.FACT_CLAIMS (
    claim_id        VARCHAR(50)     NOT NULL,
    member_key      INTEGER         REFERENCES GOLD.DIM_MEMBER(member_key),
    provider_key    INTEGER         REFERENCES GOLD.DIM_PROVIDER(provider_key),
    payer_key       INTEGER         REFERENCES GOLD.DIM_PAYER(payer_key),
    diagnosis_key   INTEGER         REFERENCES GOLD.DIM_DIAGNOSIS(diagnosis_key),
    procedure_key   INTEGER         REFERENCES GOLD.DIM_PROCEDURE(procedure_key),
    claim_amount    NUMBER(12,2),
    allowed_amount  NUMBER(12,2),
    paid_amount     NUMBER(12,2),
    status          VARCHAR(30),
    service_date    DATE,
    submission_date DATE,
    service_year_month VARCHAR(7),
    PRIMARY KEY (claim_id)
)
CLUSTER BY (service_year_month, payer_key)
COMMENT = 'Claims fact table — partitioned by service month';

CREATE OR REPLACE TABLE GOLD.FACT_ADT_EVENTS (
    event_id        VARCHAR(50)     NOT NULL,
    event_type      VARCHAR(10),
    event_description VARCHAR(100),
    member_key      INTEGER         REFERENCES GOLD.DIM_MEMBER(member_key),
    provider_key    INTEGER         REFERENCES GOLD.DIM_PROVIDER(provider_key),
    facility_name   VARCHAR(200),
    department      VARCHAR(100),
    room_number     VARCHAR(10),
    admit_reason    VARCHAR(200),
    event_timestamp TIMESTAMP_NTZ,
    event_year_month VARCHAR(7),
    PRIMARY KEY (event_id)
)
CLUSTER BY (event_year_month)
COMMENT = 'ADT events fact table — partitioned by event month';
