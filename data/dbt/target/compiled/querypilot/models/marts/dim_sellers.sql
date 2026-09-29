select
    s.seller_id,
    s.city,
    s.state,
    s.zip_prefix,
    g.lat,
    g.lng
from "warehouse"."staging"."stg_sellers" s
left join "warehouse"."staging"."stg_geolocation" g on g.zip_prefix = s.zip_prefix