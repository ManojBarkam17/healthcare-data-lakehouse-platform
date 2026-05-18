-- assert_charge_gte_paid.sql
-- Custom data test: charge amount should always be >= paid amount.
-- Violations indicate overbilling corrections or data quality issues.

select
    claim_id,
    claim_line_id,
    line_charge_amount,
    paid_amount
from {{ ref('stg_claims') }}
where line_charge_amount < paid_amount
    and line_charge_amount > 0
