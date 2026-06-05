with source as (
    select * from raw.faf_shipments
),

cleaned as (
    select
        -- Foreign keys
        fr_orig             as foreign_origin,
        fr_dest             as foreign_destination,
        fr_inmode           as foreign_inmode,
        fr_outmode          as foreign_outmode,

        -- Domestic keys
        dms_orig            as origin_zone,
        dms_dest            as destination_zone,
        dms_mode::integer   as mode_code,
        sctg2::integer      as commodity_code,
        trade_type::integer as trade_type,
        dist_band::integer  as dist_band,

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
        and dms_orig is not null and dms_orig != ''
        and dms_dest is not null and dms_dest != ''
        and sctg2 is not null and sctg2 != ''
),

final as (
    select
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key([
            'foreign_origin',
            'foreign_destination',
            'foreign_inmode',
            'foreign_outmode',
            'origin_zone',
            'destination_zone',
            'mode_code',
            'commodity_code',
            'trade_type',
            'dist_band'
        ]) }} as shipment_id,
        *
    from cleaned
)

select * from final