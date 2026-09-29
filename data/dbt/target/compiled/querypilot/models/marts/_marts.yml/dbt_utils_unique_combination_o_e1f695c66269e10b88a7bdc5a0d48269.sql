





with validation_errors as (

    select
        order_id, payment_sequence
    from "warehouse"."marts"."fct_payments"
    group by order_id, payment_sequence
    having count(*) > 1

)

select *
from validation_errors


