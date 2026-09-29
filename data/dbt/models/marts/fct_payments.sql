select
    pm.order_id,
    pm.payment_sequence,
    pm.payment_type,
    pm.installments,
    pm.payment_value,
    o.order_status,
    o.purchased_at,
    o.purchased_at::date as purchase_date
from {{ ref('stg_order_payments') }} pm
join {{ ref('stg_orders') }} o on o.order_id = pm.order_id