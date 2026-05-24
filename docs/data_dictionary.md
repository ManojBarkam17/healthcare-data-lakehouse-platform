# Data Dictionary

## Gold Layer Tables (Star Schema)

### dim_member (SCD Type 2)

| Column | Type | Description |
|--------|------|-------------|
| member_key | INTEGER | Surrogate key (auto-generated) |
| member_id | VARCHAR | Business key (e.g., MBR100001) |
| first_name | VARCHAR | Masked: first initial + asterisks |
| last_name | VARCHAR | Masked: first initial + asterisks |
| date_of_birth | DATE | Date of birth |
| gender | VARCHAR(1) | M or F |
| state | VARCHAR(2) | US state code |
| zip_code | VARCHAR(10) | ZIP code |
| plan_type | VARCHAR | Insurance plan type (HMO, PPO, etc.) |
| ssn_hash | VARCHAR(64) | SHA-256 hash of SSN (irreversible) |
| valid_from | DATE | SCD2: Record effective start date |
| valid_to | DATE | SCD2: Record effective end date (9999-12-31 if current) |
| is_current | BOOLEAN | SCD2: True if this is the active record |

### dim_provider

| Column | Type | Description |
|--------|------|-------------|
| provider_key | INTEGER | Surrogate key |
| provider_id | VARCHAR | Business key (UUID) |
| npi | VARCHAR(10) | National Provider Identifier |
| first_name | VARCHAR | Provider first name |
| last_name | VARCHAR | Provider last name |
| specialty | VARCHAR | Medical specialty (e.g., Cardiology) |
| facility_name | VARCHAR | Associated facility |
| state | VARCHAR(2) | Practice state |
| is_active | BOOLEAN | Currently active provider |

### dim_payer

| Column | Type | Description |
|--------|------|-------------|
| payer_key | INTEGER | Surrogate key |
| payer_id | VARCHAR | Business key (e.g., PAY0001) |
| payer_name | VARCHAR | Insurance company name |
| payer_type | VARCHAR | Organization type |
| plan_types_offered | VARCHAR | Available plan types |
| state | VARCHAR(2) | Headquarters state |
| is_active | BOOLEAN | Currently active payer |

### dim_diagnosis

| Column | Type | Description |
|--------|------|-------------|
| diagnosis_key | INTEGER | Surrogate key |
| icd10_code | VARCHAR | ICD-10-CM code (e.g., E11.9) |
| description | VARCHAR | Diagnosis description |

### dim_procedure

| Column | Type | Description |
|--------|------|-------------|
| procedure_key | INTEGER | Surrogate key |
| cpt_code | VARCHAR(5) | CPT procedure code (e.g., 99213) |
| description | VARCHAR | Procedure description |

### fact_claims

| Column | Type | Description |
|--------|------|-------------|
| claim_id | VARCHAR | Unique claim identifier (UUID) |
| member_key | INTEGER | FK → dim_member |
| provider_key | INTEGER | FK → dim_provider |
| payer_key | INTEGER | FK → dim_payer |
| diagnosis_key | INTEGER | FK → dim_diagnosis |
| procedure_key | INTEGER | FK → dim_procedure |
| claim_amount | DECIMAL | Total charge amount |
| allowed_amount | DECIMAL | Payer-allowed amount |
| paid_amount | DECIMAL | Amount paid by payer |
| status | VARCHAR | approved, denied, pending, partially_approved, under_review |
| service_date | DATE | Date of service |
| submission_date | DATE | Date claim was submitted |
| service_year_month | VARCHAR | Partition key (YYYY-MM) |

### fact_adt_events

| Column | Type | Description |
|--------|------|-------------|
| event_id | VARCHAR | Unique event identifier (UUID) |
| event_type | VARCHAR | HL7 event code (A01=Admit, A02=Transfer, A03=Discharge, A04=Register, A08=Update) |
| event_description | VARCHAR | Human-readable event description |
| member_key | INTEGER | FK → dim_member |
| provider_key | INTEGER | FK → dim_provider |
| facility_name | VARCHAR | Hospital/clinic name |
| department | VARCHAR | Department (e.g., Emergency, ICU) |
| room_number | VARCHAR | Room assignment |
| admit_reason | VARCHAR | Reason for admission |
| event_timestamp | TIMESTAMP | When the event occurred |
| event_year_month | VARCHAR | Partition key (YYYY-MM) |

## Reference Data

### ICD-10 Codes (20 codes)

Common diagnoses used in synthetic data: E11.9 (Diabetes), I10 (Hypertension), J06.9 (URI), M54.5 (Low back pain), and 16 others.

### CPT Codes (20 codes)

Common procedures: 99213-99215 (office visits), 99281-99285 (ED visits), 36415 (venipuncture), 80053 (metabolic panel), and 12 others.

### Claim Status Distribution

| Status | Weight | Description |
|--------|--------|-------------|
| approved | 65% | Claim fully approved |
| denied | 12% | Claim denied |
| pending | 10% | Under initial review |
| partially_approved | 8% | Partial payment |
| under_review | 5% | Additional review needed |

### ADT Event Types

| Code | Description | Weight |
|------|-------------|--------|
| A01 | Admit/Visit Notification | 25% |
| A02 | Transfer a Patient | 15% |
| A03 | Discharge/End Visit | 30% |
| A04 | Register a Patient | 20% |
| A08 | Update Patient Information | 10% |
