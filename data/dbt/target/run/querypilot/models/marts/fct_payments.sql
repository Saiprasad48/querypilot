
  
    

  create  table "warehouse"."marts"."fct_payments__dbt_tmp"
  
  
    as
  
  (
    select
    pm.order_id,
    pm.payment_sequence,
    pm.payment_type,
    pm.installments,
    pm.payment_value,
    o.order_status,
    o.purchased_at,
    o.purchased_at::date as purchase_date
from "warehouse"."staging"."stg_order_payments" pm
join "warehouse"."staging"."stg_orders" o on o.order_id = pm.order_id
  );
  