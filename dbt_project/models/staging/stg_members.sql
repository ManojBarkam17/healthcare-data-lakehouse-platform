-- stg_members.sql
-- Current-version member records from the SCD Type 2 dimension.
-- Filters to is_current = true so downstream models always see
-- the latest snapshot of each member.

with source as (
    select * from {{ source('gold', 'dim_member') }}
),

current_members as (
    select
        member_id,
        first_name,
        last_name,
        date_of_birth,
        gender,
        city,
        state,
        zip_code,
        plan_type,
        payer_id,
        effective_date,
        termination_date,
        effective_start,
        effective_end,
        is_current
    from source
    where is_current = true
)

select * from current_members
