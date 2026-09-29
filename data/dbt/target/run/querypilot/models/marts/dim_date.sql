
  
    

  create  table "warehouse"."marts"."dim_date__dbt_tmp"
  
  
    as
  
  (
    with spine as (
    





with rawdata as (

    

    

    with p as (
        select 0 as generated_number union all select 1
    ), unioned as (

    select

    
    p0.generated_number * power(2, 0)
     + 
    
    p1.generated_number * power(2, 1)
     + 
    
    p2.generated_number * power(2, 2)
     + 
    
    p3.generated_number * power(2, 3)
     + 
    
    p4.generated_number * power(2, 4)
     + 
    
    p5.generated_number * power(2, 5)
     + 
    
    p6.generated_number * power(2, 6)
     + 
    
    p7.generated_number * power(2, 7)
     + 
    
    p8.generated_number * power(2, 8)
     + 
    
    p9.generated_number * power(2, 9)
     + 
    
    p10.generated_number * power(2, 10)
    
    
    + 1
    as generated_number

    from

    
    p as p0
     cross join 
    
    p as p1
     cross join 
    
    p as p2
     cross join 
    
    p as p3
     cross join 
    
    p as p4
     cross join 
    
    p as p5
     cross join 
    
    p as p6
     cross join 
    
    p as p7
     cross join 
    
    p as p8
     cross join 
    
    p as p9
     cross join 
    
    p as p10
    
    

    )

    select *
    from unioned
    where generated_number <= 1096
    order by generated_number



),

all_periods as (

    select (
        

    cast('2016-01-01' as date) + ((interval '1 day') * (row_number() over (order by generated_number) - 1))


    ) as date_day
    from rawdata

),

filtered as (

    select *
    from all_periods
    where date_day <= cast('2019-01-01' as date)

)

select * from filtered


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
  );
  