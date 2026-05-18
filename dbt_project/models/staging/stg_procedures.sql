-- stg_procedures.sql
-- CPT-4 procedure code reference.

with source as (
    select * from {{ source('gold', 'dim_procedure') }}
),

staged as (
    select
        procedure_code,
        procedure_description,
        code_system
    from source
)

select * from staged
