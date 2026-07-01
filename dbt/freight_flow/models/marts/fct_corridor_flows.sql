with shipments as (
    select * from {{ ref('stg_faf_shipments_long') }}
),

regions as (
    select * from {{ ref('dim_regions') }}
),

commodities as (
    select * from {{ ref('dim_commodities') }}
),

modes as (
    select * from {{ ref('dim_transport_modes') }}
),

joined as (
    select
        -- Corridor identifiers
        s.origin_zone,
        s.destination_zone,
        r_orig.region_name   as origin_name,
        r_dest.region_name   as destination_name,
        r_orig.state         as origin_state,
        r_dest.state         as destination_state,

        -- Commodity
        s.commodity_code,
        c.commodity_name,
        c.commodity_category,

        -- Mode
        s.mode_code,
        m.mode_name,
        m.mode_category,

        -- Time
        s.year,

        -- Measures
        sum(s.tons)   as total_tons,
        sum(s.value)  as total_value,
        sum(s.tmiles) as total_tmiles

    from shipments s
    left join regions r_orig
        on s.origin_zone = lpad(r_orig.region_code::text, 3, '0')
    left join regions r_dest
        on s.destination_zone = lpad(r_dest.region_code::text, 3, '0')
    left join commodities c
        on s.commodity_code = c.commodity_code
    left join modes m
        on s.mode_code = m.mode_code
    group by
        s.origin_zone,
        s.destination_zone,
        r_orig.region_name,
        r_dest.region_name,
        r_orig.state,
        r_dest.state,
        s.commodity_code,
        c.commodity_name,
        c.commodity_category,
        s.mode_code,
        m.mode_name,
        m.mode_category,
        s.year
),

with_yoy as (
    select
        *,
        lag(total_tons) over (
            partition by origin_zone, destination_zone, commodity_code, mode_code
            order by year
        ) as prev_year_tons,

        round(
            LEAST(GREATEST(
                (total_tons - lag(total_tons) over (
                    partition by origin_zone, destination_zone, commodity_code, mode_code
                    order by year
                )) / nullif(lag(total_tons) over (
                    partition by origin_zone, destination_zone, commodity_code, mode_code
                    order by year
                ), 0) * 100,
            -100), 1000)
        , 2) as yoy_growth_pct

    from joined
)

select * from with_yoy