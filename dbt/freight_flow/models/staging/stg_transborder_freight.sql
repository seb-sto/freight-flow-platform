with source as (
    select * from raw.transborder_freight
),

cleaned as (
    select
        -- Keys
        trdtype::integer        as trade_type,
        usastate                as usa_state,
        commodity2              as commodity_code,
        disagmot::integer       as mode_code,
        mexstate                as mexico_state,
        canprov                 as canada_province,
        country::integer        as country_code,
        df::integer             as domestic_foreign_flag,
        contcode                as container_code,

        -- Measures
        value::numeric          as shipment_value,
        shipwt::numeric         as ship_weight,
        freight_charges::numeric as freight_charges,

        -- Time
        month::integer          as month,
        year::integer           as year

    from source
    where
        value is not null
        and usastate is not null and usastate != ''
        and commodity2 is not null and commodity2 != ''
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key([
            'trade_type',
            'usa_state',
            'commodity_code',
            'mode_code',
            'mexico_state',
            'canada_province',
            'country_code',
            'domestic_foreign_flag',
            'container_code',
            'month',
            'year'
        ]) }} as transborder_id,
        *
    from cleaned
)

select * from final