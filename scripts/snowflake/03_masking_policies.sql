-- =============================================================================
-- Snowflake Dynamic Data Masking — Healthcare Data Lakehouse
-- =============================================================================
-- Implements column-level masking policies for PHI/PII fields.
-- In production, these policies ensure analysts never see raw PHI
-- even when querying Bronze tables directly.
--
-- Masking is applied transparently based on the user's role.
-- =============================================================================

USE DATABASE HEALTHCARE_LAKEHOUSE;

-- ---------------------------------------------------------------------------
-- SSN Masking Policy
-- Engineers see full SSN; analysts see masked version (***-**-XXXX)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE MASKING POLICY BRONZE.SSN_MASK AS (val VARCHAR)
RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('HEALTHCARE_ENGINEER') THEN val
        WHEN CURRENT_ROLE() IN ('HEALTHCARE_ANALYST')  THEN '***-**-' || RIGHT(val, 4)
        ELSE '***-**-****'
    END
COMMENT = 'Masks SSN based on role. Engineers see full, analysts see last 4.';

-- Apply to Bronze members table
ALTER TABLE BRONZE.RAW_MEMBERS
    MODIFY COLUMN ssn SET MASKING POLICY BRONZE.SSN_MASK;

-- ---------------------------------------------------------------------------
-- Name Masking Policy
-- Engineers see full name; others see first initial only
-- ---------------------------------------------------------------------------
CREATE OR REPLACE MASKING POLICY BRONZE.NAME_MASK AS (val VARCHAR)
RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('HEALTHCARE_ENGINEER') THEN val
        ELSE LEFT(val, 1) || REPEAT('*', LENGTH(val) - 1)
    END
COMMENT = 'Masks names to first initial. Engineers see full name.';

-- Apply to Bronze members
ALTER TABLE BRONZE.RAW_MEMBERS
    MODIFY COLUMN first_name SET MASKING POLICY BRONZE.NAME_MASK;
ALTER TABLE BRONZE.RAW_MEMBERS
    MODIFY COLUMN last_name SET MASKING POLICY BRONZE.NAME_MASK;

-- ---------------------------------------------------------------------------
-- Phone Masking Policy
-- Only engineers see full phone numbers
-- ---------------------------------------------------------------------------
CREATE OR REPLACE MASKING POLICY BRONZE.PHONE_MASK AS (val VARCHAR)
RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('HEALTHCARE_ENGINEER') THEN val
        ELSE '(***) ***-' || RIGHT(REGEXP_REPLACE(val, '[^0-9]', ''), 4)
    END
COMMENT = 'Masks phone numbers, showing last 4 digits only.';

ALTER TABLE BRONZE.RAW_MEMBERS
    MODIFY COLUMN phone SET MASKING POLICY BRONZE.PHONE_MASK;

-- ---------------------------------------------------------------------------
-- Email Masking Policy
-- ---------------------------------------------------------------------------
CREATE OR REPLACE MASKING POLICY BRONZE.EMAIL_MASK AS (val VARCHAR)
RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('HEALTHCARE_ENGINEER') THEN val
        ELSE LEFT(val, 1) || '***@' || SPLIT_PART(val, '@', 2)
    END
COMMENT = 'Masks email to first character + domain only.';

ALTER TABLE BRONZE.RAW_MEMBERS
    MODIFY COLUMN email SET MASKING POLICY BRONZE.EMAIL_MASK;

-- ---------------------------------------------------------------------------
-- Verify masking policies
-- ---------------------------------------------------------------------------
-- Run as different roles to see masking in action:
--
-- USE ROLE HEALTHCARE_ENGINEER;
-- SELECT member_id, ssn, first_name, phone, email
-- FROM BRONZE.RAW_MEMBERS LIMIT 5;
-- Result: Full values visible
--
-- USE ROLE HEALTHCARE_ANALYST;
-- SELECT member_id, ssn, first_name, phone, email
-- FROM BRONZE.RAW_MEMBERS LIMIT 5;
-- Result: SSN=***-**-6789, name=J***, phone=(***) ***-1234, email=j***@example.com
