with source as (
    select * from raw.supply_chain_indicators
),

cleaned as (
    select
        mode                                    as transport_mode,
        indicator                               as indicator_name,
        week_number::integer                    as week_number,
        to_date(
            split_part(week_ending, ' ', 1),
            'MM/DD/YYYY'
        )                                       as week_ending_date,
        extract(year from to_date(
            split_part(week_ending, ' ', 1),
            'MM/DD/YYYY'
        ))::integer                             as year,
        pct_change::numeric                     as pct_change_from_baseline

    from source
    where week_ending is not null
)

select * from cleaned