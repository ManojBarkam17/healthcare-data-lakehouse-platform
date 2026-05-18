-- assert_valid_risk_tiers.sql
-- Custom data test: every member must have a valid risk tier assigned.

select
    member_id,
    risk_tier
from {{ ref('mart_member_risk') }}
where risk_tier not in ('Low', 'Medium', 'High', 'Very High')
    or risk_tier is null
