select
    s.seller_id,
    s.city,
    s.state,
    s.zip_prefix,
    g.lat,
    g.lng
from {{ ref('stg_sellers') }} s
left join {{ ref('stg_geolocation') }} g on g.zip_prefix = s.zip_prefix