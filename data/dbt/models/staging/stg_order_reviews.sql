with source as (
    select * from {{ source('olist', 'order_reviews') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by order_id
            order by review_answer_timestamp::timestamp desc nulls last,
                     review_creation_date::timestamp desc
        ) as rn
    from source
)

select
    review_id,
    order_id,
    review_score::int                     as review_score,
    review_comment_title                  as comment_title,
    review_comment_message                as comment_message,
    review_creation_date::timestamp       as created_at,
    review_answer_timestamp::timestamp    as answered_at
from ranked
where rn = 1