
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    zip_prefix as unique_field,
    count(*) as n_records

from "warehouse"."staging"."stg_geolocation"
where zip_prefix is not null
group by zip_prefix
having count(*) > 1



  
  
      
    ) dbt_internal_test