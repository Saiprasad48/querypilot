with source as (
    select * from {{ source('olist', 'geolocation') }}
)

select
    geolocation_zip_code_prefix                               as zip_prefix,
    avg(geolocation_lat::numeric)::numeric(9, 6)              as lat,
    avg(geolocation_lng::numeric)::numeric(9, 6)              as lng,
    mode() within group (order by geolocation_city)           as city,
    mode() within group (order by upper(geolocation_state))   as state
from source
group by 1