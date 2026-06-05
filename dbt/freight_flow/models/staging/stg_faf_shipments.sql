with source as (
    select * from raw.faf_shipments
),

cleaned as (
    select
        -- Keys
        fr_orig::integer        as origin_zone,
        fr_dest::integer        as destination_zone,
        dms_orig::integer       as dms_origin,
        dms_dest::integer       as dms_destination,
        sctg2::integer          as commodity_code,
        dms_mode::integer       as mode_code,
        trade_type::integer     as trade_type,

        -- Actuals: tons (stored as thousands in FAF)
        tons_2017::numeric      as tons_2017,
        tons_2018::numeric      as tons_2018,
        tons_2019::numeric      as tons_2019,
        tons_2020::numeric      as tons_2020,
        tons_2021::numeric      as tons_2021,
        tons_2022::numeric      as tons_2022,
        tons_2023::numeric      as tons_2023,
        tons_2024::numeric      as tons_2024,

        -- Actuals: value (millions of dollars)
        value_2017::numeric     as value_2017,
        value_2018::numeric     as value_2018,
        value_2019::numeric     as value_2019,
        value_2020::numeric     as value_2020,
        value_2021::numeric     as value_2021,
        value_2022::numeric     as value_2022,
        value_2023::numeric     as value_2023,
        value_2024::numeric     as value_2024,

        -- Actuals: ton-miles (millions)
        tmiles_2017::numeric    as tmiles_2017,
        tmiles_2018::numeric    as tmiles_2018,
        tmiles_2019::numeric    as tmiles_2019,
        tmiles_2020::numeric    as tmiles_2020,
        tmiles_2021::numeric    as tmiles_2021,
        tmiles_2022::numeric    as tmiles_2022,
        tmiles_2023::numeric    as tmiles_2023,
        tmiles_2024::numeric    as tmiles_2024

    from source
    where
        tons_2017::numeric >= 0
        and fr_orig is not null
        and fr_dest is not null
        and sctg2 is not null
),

final as (
    select
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key([
            'origin_zone',
            'destination_zone',
            'commodity_code',
            'mode_code',
            'trade_type'
        ]) }} as shipment_id,
        *
    from cleaned
)

select * from final