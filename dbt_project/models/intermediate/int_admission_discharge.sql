-- int_admission_discharge.sql
-- Pairs admission (A01) and discharge (A03) events to calculate
-- length of stay (LOS) — a key utilization metric.

with admissions as (
    select
        member_id,
        facility_name,
        department,
        event_timestamp as admit_timestamp,
        admit_reason,
        row_number() over (
            partition by member_id, facility_name
            order by event_timestamp
        ) as admit_seq
    from {{ ref('stg_adt_events') }}
    where event_type = 'A01'
),

discharges as (
    select
        member_id,
        facility_name,
        event_timestamp as discharge_timestamp,
        row_number() over (
            partition by member_id, facility_name
            order by event_timestamp
        ) as discharge_seq
    from {{ ref('stg_adt_events') }}
    where event_type = 'A03'
),

paired as (
    select
        a.member_id,
        a.facility_name,
        a.department,
        a.admit_reason,
        a.admit_timestamp,
        d.discharge_timestamp,
        -- Length of stay in days (0 = same-day discharge)
        cast(
            date_diff('day', a.admit_timestamp, d.discharge_timestamp)
            as decimal(10, 2)
        ) as length_of_stay_days
    from admissions a
    left join discharges d
        on a.member_id = d.member_id
        and a.facility_name = d.facility_name
        and a.admit_seq = d.discharge_seq
)

select * from paired
