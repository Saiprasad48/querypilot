with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2016-01-01' as date)",
        end_date="cast('2019-01-01' as date)"
    ) }}
)

select
    date_day::date                                   as date_day,
    extract(year from date_day)::int                 as year,
    extract(quarter from date_day)::int              as quarter,
    extract(month from date_day)::int                as month,
    to_char(date_day, 'Mon')                         as month_name,
    date_trunc('month', date_day)::date              as month_start,
    date_trunc('week', date_day)::date               as week_start,
    extract(isodow from date_day)::int               as day_of_week,
    to_char(date_day, 'Dy')                          as day_name,
    extract(isodow from date_day) in (6, 7)          as is_weekend
from spine