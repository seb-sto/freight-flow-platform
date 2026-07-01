with corridor_flows as (
    select * from {{ ref('fct_corridor_flows') }}
),

corridor_summary as (
    select
        origin_zone,
        destination_zone,
        origin_name,
        destination_name,
        origin_state,
        destination_state,
        year,
        sum(total_tons)   as total_tons,
        sum(total_value)  as total_value,
        sum(total_tmiles) as total_tmiles,
        count(distinct mode_code) as mode_count,
        count(distinct commodity_code) as commodity_count,
        avg(yoy_growth_pct) as avg_yoy_growth_pct
    from corridor_flows
    group by
        origin_zone,
        destination_zone,
        origin_name,
        destination_name,
        origin_state,
        destination_state,
        year
),

latest_year as (
    select * from corridor_summary
    where year = (select max(year) from corridor_summary)
    and origin_zone != destination_zone
),

scored as (
    select
        *,
        percent_rank() over (order by total_tons)          as volume_pct_rank,
        percent_rank() over (order by total_value)         as value_pct_rank,
        percent_rank() over (order by avg_yoy_growth_pct)  as growth_pct_rank,
        percent_rank() over (order by mode_count)          as diversity_pct_rank
    from latest_year
),

final as (
    select
        *,
        round((
            0.35 * volume_pct_rank +
            0.30 * value_pct_rank +
            0.25 * growth_pct_rank +
            0.10 * diversity_pct_rank
        )::numeric, 4) as composite_score,

        rank() over (
            order by (
                0.35 * volume_pct_rank +
                0.30 * value_pct_rank +
                0.25 * growth_pct_rank +
                0.10 * diversity_pct_rank
            ) desc
        ) as corridor_rank

    from scored
)

select * from final
where corridor_rank <= 25
order by corridor_rank