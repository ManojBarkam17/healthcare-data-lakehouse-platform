-- stg_adt_events.sql
-- Admit/Discharge/Transfer events with decoded event types.

with source as (
    select * from {{ source('gold', 'fact_adt_events') }}
),

staged as (
    select
        event_id,
        event_type,
        -- Decode HL7 ADT event types for readability
        case event_type
            when 'A01' then 'Admission'
            when 'A02' then 'Transfer'
            when 'A03' then 'Discharge'
            when 'A04' then 'Registration'
            when 'A08' then 'Update'
            else 'Unknown'
        end as event_type_description,
        event_description,
        member_id,
        provider_id,
        facility_name,
        department,
        room_number,
        admit_reason,
        event_timestamp,
        event_year_month
    from source
)

select * from staged
