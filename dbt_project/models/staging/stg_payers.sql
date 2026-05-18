-- stg_payers.sql
-- Insurance payer/plan records.

with source as (
    select * from {{ source('gold', 'dim_payer') }}
),

staged as (
    select
        payer_id,
        payer_name,
        payer_type,
        state,
        is_active
    from source
)

select * from staged
