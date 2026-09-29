with customers as (
    select * from "warehouse"."staging"."stg_customers"
),

orders as (
    select * from "warehouse"."staging"."stg_orders"
),

payments as (
    select order_id, sum(payment_value) as payment_value
    from "warehouse"."staging"."stg_order_payments"
    group by 1
),

customer_orders as (
    select
        c.customer_unique_id,
        c.city,
        c.state,
        o.order_id,
        o.order_status,
        o.purchased_at,
        p.payment_value,
        row_number() over (
            partition by c.customer_unique_id order by o.purchased_at desc
        ) as recency_rank
    from customers c
    join orders o on o.customer_id = c.customer_id
    left join payments p on p.order_id = o.order_id
)

select
    customer_unique_id                                              as customer_id,
    max(case when recency_rank = 1 then city end)                   as city,
    max(case when recency_rank = 1 then state end)                  as state,
    min(purchased_at)                                               as first_order_at,
    max(purchased_at)                                               as last_order_at,
    count(*)                                                        as order_count,
    count(*) filter (where order_status = 'delivered')              as delivered_order_count,
    coalesce(sum(payment_value) filter (where order_status = 'delivered'), 0)::numeric(12, 2)
                                                                    as lifetime_revenue,
    count(*) filter (where order_status = 'delivered') > 1          as is_repeat_customer
from customer_orders
group by 1