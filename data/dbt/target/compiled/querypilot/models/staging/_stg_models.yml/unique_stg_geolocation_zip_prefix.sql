
    
    

select
    zip_prefix as unique_field,
    count(*) as n_records

from "warehouse"."staging"."stg_geolocation"
where zip_prefix is not null
group by zip_prefix
having count(*) > 1


