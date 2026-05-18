-- stg_diagnoses.sql
-- ICD-10-CM diagnosis code reference.

with source as (
    select * from {{ source('gold', 'dim_diagnosis') }}
),

staged as (
    select
        diagnosis_code,
        diagnosis_description,
        code_system,
        -- Extract the ICD-10 chapter (first character)
        substring(diagnosis_code, 1, 1) as icd10_chapter
    from source
)

select * from staged
