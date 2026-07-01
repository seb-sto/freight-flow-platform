with corridor_flows as (
    select * from {{ ref('fct_corridor_flows') }}
),

corridor_totals as (
    -- Total tonnage per corridor per year across all modes
    select
        origin_zone,
        destination_zone,
        origin_name,
        destination_name,
        origin_state,
        destination_state,
        year,
        sum(total_tons) as corridor_total_tons
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

mode_shares as (
    select
        cf.origin_zone,
        cf.destination_zone,
        cf.origin_name,
        cf.destination_name,
        cf.origin_state,
        cf.destination_state,
        cf.mode_code,
        cf.mode_name,
        cf.mode_category,
        cf.year,
        sum(cf.total_tons) as mode_tons,
        ct.corridor_total_tons,

        -- Mode share percentage
        round(
            sum(cf.total_tons) / nullif(ct.corridor_total_tons, 0) * 100,
        2) as mode_share_pct

    from corridor_flows cf
    join corridor_totals ct
        on cf.origin_zone = ct.origin_zone
        and cf.destination_zone = ct.destination_zone
        and cf.year = ct.year
    where ct.corridor_total_tons > 0  -- add this
    group by
        cf.origin_zone,
        cf.destination_zone,
        cf.origin_name,
        cf.destination_name,
        cf.origin_state,
        cf.destination_state,
        cf.mode_code,
        cf.mode_name,
        cf.mode_category,
        cf.year,
        ct.corridor_total_tons
),

with_shift_detection as (
    select
        *,
        lag(mode_share_pct) over (
            partition by origin_zone, destination_zone, mode_code
            order by year
        ) as prev_year_share_pct,

        -- Flag corridors where truck share dropped >5% YoY (truck-to-rail migration)
        case
            when mode_name = 'Truck'
            and (mode_share_pct - lag(mode_share_pct) over (
                partition by origin_zone, destination_zone, mode_code
                order by year
            )) < -5
            then true
            else false
        end as truck_share_decline_flag

    from mode_shares
)

select * from with_shift_detection