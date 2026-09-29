{{ config(indexes=[
    {'columns': ['purchase_date']},
    {'columns': ['customer_id']},
    {'columns': ['customer_state']}
]) }}

with orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

items as (
    select
        order_id,
        count(*)                  as item_count,
        count(distinct seller_id) as seller_count,
        sum(price)                as items_value,
        sum(freight_value)        as freight_value
    from {{ ref('stg_order_items') }}
    group by 1
),

payments as (
    select
        order_id,
        sum(payment_value)                                        as payment_value,
        max(installments)                                         as max_installments,
        (array_agg(payment_type order by payment_value desc))[1]  as main_payment_type
    from {{ ref('stg_order_payments') }}
    group by 1
),

reviews as (
    select order_id, review_score from {{ ref('stg_order_reviews') }}
)

select
    o.order_id,
    c.customer_unique_id                                        as customer_id,
    c.city                                                      as customer_city,
    c.state                                                     as customer_state,
    o.order_status,
    o.order_status = 'delivered'                                as is_delivered,
    o.purchased_at,
    o.purchased_at::date                                        as purchase_date,
    o.approved_at,
    o.shipped_at,
    o.delivered_at,
    o.estimated_delivery_at,
    coalesce(i.item_count, 0)                                   as item_count,
    coalesce(i.seller_count, 0)                                 as seller_count,
    coalesce(i.items_value, 0)::numeric(12, 2)                  as items_value,
    coalesce(i.freight_value, 0)::numeric(12, 2)                as freight_value,
    (coalesce(i.items_value, 0) + coalesce(i.freight_value, 0))::numeric(12, 2)
                                                                as order_value,
    coalesce(p.payment_value, 0)::numeric(12, 2)               as payment_value,
    p.main_payment_type,
    p.max_installments,
    r.review_score,
    round((extract(epoch from (o.delivered_at - o.purchased_at)) / 86400)::numeric, 1)
                                                                as delivery_days,
    case
        when o.delivered_at is null then null
        else o.delivered_at::date > o.estimated_delivery_at::date
    end                                                         as is_late
from orders o
left join customers c on c.customer_id = o.customer_id
left join items     i on i.order_id    = o.order_id
left join payments  p on p.order_id    = o.order_id
left join reviews   r on r.order_id    = o.order_id