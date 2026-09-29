
    
    select
      count(*) as failures,
      count(*) >0 as should_warn,
      count(*) >1000 as should_error
    from (
      
    
  

select order_id, order_value, payment_value
from "warehouse"."marts"."fct_orders"
where is_delivered
  and abs(payment_value - order_value) > 5
  
  
      
    ) dbt_internal_test