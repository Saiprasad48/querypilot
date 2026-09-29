

select order_id, order_value, payment_value
from "warehouse"."marts"."fct_orders"
where is_delivered
  and abs(payment_value - order_value) > 5