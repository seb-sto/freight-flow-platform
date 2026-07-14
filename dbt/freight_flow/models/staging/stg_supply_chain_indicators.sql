with source as (
    select * from raw.supply_chain_indicators
),

cleaned as (
    select
        to_date(obs_date, 'MM/DD/YYYY')     as obs_date,
        extract(year from to_date(obs_date, 'MM/DD/YYYY'))::integer as year,
        extract(month from to_date(obs_date, 'MM/DD/YYYY'))::integer as month,

        -- Freight Transportation Services Index
        tsi_freight::numeric                as tsi_freight,
        tsi_freight_c::numeric              as tsi_freight_pct_change,

        -- Truck
        vmt::numeric                        as truck_vmt,

        -- Rail
        rail_frt_carloads::numeric          as rail_carloads,
        rail_frt_intermodal::numeric        as rail_intermodal,

        -- Pipeline
        petroleum::numeric                  as petroleum_pipeline,
        natural_gas::numeric                as natural_gas_pipeline,

        -- Waterborne
        waterborne::numeric                 as waterborne_freight,

        -- Economic indicators
        inv_to_sales::numeric               as inventory_to_sales_ratio,
        ind_pro::numeric                    as industrial_production_index

    from source
    where obs_date is not null
)

select * from cleaned