
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select zip_prefix
from "warehouse"."staging"."stg_geolocation"
where zip_prefix is null



  
  
      
    ) dbt_internal_test