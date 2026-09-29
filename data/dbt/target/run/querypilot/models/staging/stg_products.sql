
  create view "warehouse"."staging"."stg_products__dbt_tmp"
    
    
  as (
    with products as (
    select * from "warehouse"."raw"."products"
),

translation as (
    select * from "warehouse"."raw"."category_translation"
)

select
    p.product_id,
    coalesce(t.product_category_name_english, p.product_category_name, 'unknown') as category,
    p.product_category_name                       as category_pt,
    p.product_name_lenght::numeric::int           as name_length,
    p.product_description_lenght::numeric::int    as description_length,
    p.product_photos_qty::numeric::int            as photo_count,
    p.product_weight_g::numeric                   as weight_g,
    p.product_length_cm::numeric                  as length_cm,
    p.product_height_cm::numeric                  as height_cm,
    p.product_width_cm::numeric                   as width_cm
from products p
left join translation t using (product_category_name)
  );