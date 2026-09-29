select
    product_id,
    category,
    category_pt,
    photo_count,
    weight_g,
    length_cm,
    height_cm,
    width_cm,
    (length_cm * height_cm * width_cm)::numeric(14, 1) as volume_cm3
from "warehouse"."staging"."stg_products"