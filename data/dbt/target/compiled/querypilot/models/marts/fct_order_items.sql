select
    i.order_id,
    i.item_number,
    i.product_id,
    i.seller_id,
    p.category,
    i.price,
    i.freight_value,
    (i.price + i.freight_value)::numeric(12, 2)  as item_total,
    o.order_status,
    o.purchased_at,
    o.purchased_at::date                         as purchase_date,
    c.state                                      as customer_state,
    s.state                                      as seller_state
from "warehouse"."staging"."stg_order_items" i
join "warehouse"."staging"."stg_orders"         o on o.order_id    = i.order_id
left join "warehouse"."staging"."stg_customers" c on c.customer_id = o.customer_id
left join "warehouse"."staging"."stg_products"  p on p.product_id  = i.product_id
left join "warehouse"."staging"."stg_sellers"   s on s.seller_id   = i.seller_id