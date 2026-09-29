
  create view "warehouse"."staging"."stg_order_payments__dbt_tmp"
    
    
  as (
    with source as (
    select * from "warehouse"."raw"."order_payments"
)

select
    order_id,
    payment_sequential::int            as payment_sequence,
    payment_type,
    payment_installments::int          as installments,
    payment_value::numeric(12, 2)      as payment_value
from source
  );