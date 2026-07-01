with corridor_flows as (
    select * from {{ ref('fct_corridor_flows') }}
),

aggregated as (
    select
        commodity_code,
        commodity_name,
        commodity_category,
        year,

        -- Volume metrics
        sum(total_tons)   as total_tons,
        sum(total_value)  as total_value,
        sum(total_tmiles) as total_tmiles,

        -- Value per ton (efficiency metric)
        round(
            sum(total_value) / nullif(sum(total_tons), 0),
        4) as value_per_ton,

        -- Rank by tonnage within each year
        rank() over (
            partition by year
            order by sum(total_tons) desc
        ) as tonnage_rank

    from corridor_flows
    group by
        commodity_code,
        commodity_name,
        commodity_category,
        year
),

with_yoy as (
    select
        *,
        lag(total_tons) over (
            partition by commodity_code
            order by year
        ) as prev_year_tons,

        round(
            (total_tons - lag(total_tons) over (
                partition by commodity_code
                order by year
            )) / nullif(lag(total_tons) over (
                partition by commodity_code
                order by year
            ), 0) * 100,
        2) as yoy_growth_pct

    from aggregated
)

select * from with_yoy