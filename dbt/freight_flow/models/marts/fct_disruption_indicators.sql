with indicators as (
    select * from {{ ref('stg_supply_chain_indicators') }}
),

with_zscore as (
    select
        *,
        avg(tsi_freight) over (
            partition by month
        ) as avg_tsi_by_month,

        stddev(tsi_freight) over (
            partition by month
        ) as stddev_tsi_by_month,

        avg(truck_vmt) over (
            partition by month
        ) as avg_vmt_by_month,

        stddev(truck_vmt) over (
            partition by month
        ) as stddev_vmt_by_month

    from indicators
),

with_anomaly as (
    select
        obs_date,
        year,
        month,
        tsi_freight,
        tsi_freight_pct_change,
        truck_vmt,
        rail_carloads,
        petroleum_pipeline,
        waterborne_freight,
        inventory_to_sales_ratio,

        -- Z-scores partitioned by month to account for seasonality
        round(
            (tsi_freight - avg_tsi_by_month) /
            nullif(stddev_tsi_by_month, 0)
        , 2) as tsi_zscore,

        round(
            (truck_vmt - avg_vmt_by_month) /
            nullif(stddev_vmt_by_month, 0)
        , 2) as vmt_zscore,

        -- Anomaly flag on either metric
        case
            when abs(
                (tsi_freight - avg_tsi_by_month) /
                nullif(stddev_tsi_by_month, 0)
            ) > 2
            or abs(
                (truck_vmt - avg_vmt_by_month) /
                nullif(stddev_vmt_by_month, 0)
            ) > 2
            then true
            else false
        end as is_anomaly,

        -- Severity based on worst z-score
        case
            when greatest(
                abs((tsi_freight - avg_tsi_by_month) / nullif(stddev_tsi_by_month, 0)),
                abs((truck_vmt - avg_vmt_by_month) / nullif(stddev_vmt_by_month, 0))
            ) > 3 then 'HIGH'
            when greatest(
                abs((tsi_freight - avg_tsi_by_month) / nullif(stddev_tsi_by_month, 0)),
                abs((truck_vmt - avg_vmt_by_month) / nullif(stddev_vmt_by_month, 0))
            ) > 2 then 'MEDIUM'
            else 'NORMAL'
        end as severity

    from with_zscore
)

select * from with_anomaly
order by obs_date