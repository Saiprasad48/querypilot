{{ config(severity='error', warn_if='>0', error_if='>1000') }}

select order_id, order_value, payment_value
from {{ ref('fct_orders') }}
where is_delivered
  and abs(payment_value - order_value) > 5