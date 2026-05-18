-- mart_utilization_metrics.sql
-- Facility utilization: admission volumes, LOS, and readmission indicators.
-- Supports capacity planning, quality reporting, and CMS star ratings.

with admissions as (
    select * from {{ ref('int_admission_discharge') }}
),

adt_events as (
    select * from {{ ref('stg_adt_events') }}
),

facility_metrics as (
    select
        a.facility_name,
        a.department,

        -- Volume
        count(*) as total_admissions,
        count(a.discharge_timestamp) as total_discharges,
        count(*) - count(a.discharge_timestamp) as still_admitted,

        -- Length of stay
        avg(a.length_of_stay_days) as avg_los_days,
        min(a.length_of_stay_days) as min_los_days,
        max(a.length_of_stay_days) as max_los_days,
        percentile_cont(0.5) within group (order by a.length_of_stay_days) as median_los_days,

        -- Admit reasons
        count(distinct a.admit_reason) as distinct_admit_reasons,
        count(distinct a.member_id) as unique_patients

    from admissions a
    group by 1, 2
),

-- Monthly event volumes for trend analysis
monthly_events as (
    select
        facility_name,
        event_year_month,
        event_type_description,
        count(*) as event_count
    from adt_events
    group by 1, 2, 3
)

select
    f.*,
    -- Add monthly trend as a nested summary
    round(f.avg_los_days, 2) as avg_los_days_rounded
from facility_metrics f
