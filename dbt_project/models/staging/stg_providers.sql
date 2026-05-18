-- stg_providers.sql
-- Active healthcare providers with specialty classification.

with source as (
    select * from {{ source('gold', 'dim_provider') }}
),

staged as (
    select
        provider_id,
        npi,
        first_name,
        last_name,
        first_name || ' ' || last_name as provider_full_name,
        specialty,
        facility_name,
        city,
        state,
        zip_code,
        is_active
    from source
)

select * from staged
