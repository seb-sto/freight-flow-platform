with source as (
    select * from {{ ref('stg_faf_shipments') }}
),

unpivoted as (
    -- Unpivot tons, value, and tmiles from wide to long format
    -- One row per shipment-year combination

    {% set years = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024] %}

    {% for year in years %}
    select
        shipment_id,
        foreign_origin,
        foreign_destination,
        foreign_inmode,
        foreign_outmode,
        origin_zone,
        destination_zone,
        mode_code,
        commodity_code,
        trade_type,
        dist_band,
        {{ year }} as year,
        tons_{{ year }} as tons,
        value_{{ year }} as value,
        tmiles_{{ year }} as tmiles
    from source
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select * from unpivoted