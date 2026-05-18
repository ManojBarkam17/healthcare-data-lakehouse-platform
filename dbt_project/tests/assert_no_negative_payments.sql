-- assert_no_negative_payments.sql
-- Custom data test: ensure no claim lines have negative paid amounts.
-- This would catch ETL bugs where refunds are miscoded as negative payments.

select
    claim_id,
    claim_line_id,
    paid_amount
from {{ ref('stg_claims') }}
where paid_amount < 0
