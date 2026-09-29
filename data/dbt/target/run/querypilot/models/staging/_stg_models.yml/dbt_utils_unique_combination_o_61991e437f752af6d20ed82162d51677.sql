
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  





with validation_errors as (

    select
        order_id, item_number
    from "warehouse"."staging"."stg_order_items"
    group by order_id, item_number
    having count(*) > 1

)

select *
from validation_errors



  
  
      
    ) dbt_internal_test