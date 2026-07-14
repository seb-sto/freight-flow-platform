with indicators as (
    select * from {{ ref('stg_supply_chain_indicators') }}
),

-- Z-score anomaly detection per mode/indicator
with_zscore as (
    select
        *,
        avg(pct_change_from_baseline) over (
            partition by transport_mode, indicator_name
        ) as mean_pct_change,

        stddev(pct_change_from_baseline) over (
            partition by transport_mode, indicator_name
        ) as stddev_pct_change

    from indicators
),

with_anomaly as (
    select
        transport_mode,
        indicator_name,
        week_number,
        week_ending_date,
        year,
        pct_change_from_baseline,
        mean_pct_change,
        stddev_pct_change,

        -- Z-score: how many standard deviations from the mean
        round(
            (pct_change_from_baseline - mean_pct_change) /
            nullif(stddev_pct_change, 0)
        , 2) as z_score,

        -- Flag anomalies where Z-score exceeds threshold
        case
            when abs(
                (pct_change_from_baseline - mean_pct_change) /
                nullif(stddev_pct_change, 0)
            ) > 2 then true
            else false
        end as is_anomaly,

        -- Severity classification
        case
            when abs(
                (pct_change_from_baseline - mean_pct_change) /
                nullif(stddev_pct_change, 0)
            ) > 3 then 'HIGH'
            when abs(
                (pct_change_from_baseline - mean_pct_change) /
                nullif(stddev_pct_change, 0)
            ) > 2 then 'MEDIUM'
            else 'NORMAL'
        end as severity

    from with_zscore
)

select * from with_anomaly
order by week_ending_date, transport_mode