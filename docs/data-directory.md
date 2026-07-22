# Data Dictionary
 
Column definitions for all gold layer models in the Freight Flow Intelligence Platform.
 
---
 
## `fct_corridor_flows`
 
One row per origin-destination corridor, commodity, mode, and year combination. The core fact table powering corridor-level freight analysis.
 
| Column | Type | Description |
|--------|------|-------------|
| `origin_zone` | TEXT | FAF zone code for the origin region (3-digit, e.g. `481` for Austin TX) |
| `destination_zone` | TEXT | FAF zone code for the destination region |
| `origin_name` | TEXT | Human-readable origin region name (e.g. `Houston TX`) |
| `destination_name` | TEXT | Human-readable destination region name |
| `origin_state` | TEXT | Two-letter state code for the origin region |
| `destination_state` | TEXT | Two-letter state code for the destination region |
| `commodity_code` | INTEGER | SCTG two-digit commodity code |
| `commodity_name` | TEXT | Human-readable commodity name (e.g. `Basic chemicals`) |
| `commodity_category` | TEXT | Commodity category grouping (e.g. `Chemicals`, `Energy`, `Agriculture`) |
| `mode_code` | INTEGER | FAF transport mode code |
| `mode_name` | TEXT | Human-readable mode name (e.g. `Truck`, `Rail`, `Pipeline`) |
| `mode_category` | TEXT | Mode category grouping (e.g. `Surface`, `Maritime`) |
| `year` | INTEGER | Reference year (2017–2024) |
| `total_tons` | NUMERIC | Total freight tonnage in thousands of tons |
| `total_value` | NUMERIC | Total freight value in millions of 2017 constant dollars |
| `total_tmiles` | NUMERIC | Total ton-miles in millions |
| `prev_year_tons` | NUMERIC | Prior year tonnage for the same corridor/commodity/mode combination |
| `yoy_growth_pct` | NUMERIC | Year-over-year tonnage growth percentage, capped between -100% and +1000% |
 
**Notes:**
- Tonnage values are in thousands of tons as stored in FAF5 (e.g. `18343` = 18.3 million tons)
- Value is in millions of 2017 constant dollars
- `yoy_growth_pct` is NULL for 2017 (no prior year available)
- Growth rates are capped to exclude outliers caused by near-zero base values
---
 
## `fct_commodity_trends`
 
One row per commodity and year. Aggregated time series for trend analysis across all corridors and modes.
 
| Column | Type | Description |
|--------|------|-------------|
| `commodity_code` | INTEGER | SCTG two-digit commodity code |
| `commodity_name` | TEXT | Human-readable commodity name |
| `commodity_category` | TEXT | Commodity category grouping |
| `year` | INTEGER | Reference year (2017–2024) |
| `total_tons` | NUMERIC | Total national tonnage in thousands of tons |
| `total_value` | NUMERIC | Total national value in millions of 2017 constant dollars |
| `total_tmiles` | NUMERIC | Total national ton-miles in millions |
| `value_per_ton` | NUMERIC | Average value per ton (total_value / total_tons), rounded to 4 decimal places |
| `tonnage_rank` | INTEGER | Rank of this commodity by total tonnage within each year (1 = highest) |
| `prev_year_tons` | NUMERIC | Prior year tonnage for the same commodity |
| `yoy_growth_pct` | NUMERIC | Year-over-year tonnage growth percentage |
 
**Notes:**
- Aggregated across all origin-destination corridors and transport modes
- `tonnage_rank` resets each year — rank 1 in 2017 is not necessarily rank 1 in 2024
- `yoy_growth_pct` is NULL for 2017
---
 
## `fct_mode_share`
 
One row per corridor, mode, and year. Shows the percentage of freight tonnage carried by each transport mode per corridor.
 
| Column | Type | Description |
|--------|------|-------------|
| `origin_zone` | TEXT | FAF zone code for the origin region |
| `destination_zone` | TEXT | FAF zone code for the destination region |
| `origin_name` | TEXT | Human-readable origin region name |
| `destination_name` | TEXT | Human-readable destination region name |
| `origin_state` | TEXT | Two-letter state code for the origin |
| `destination_state` | TEXT | Two-letter state code for the destination |
| `mode_code` | INTEGER | FAF transport mode code |
| `mode_name` | TEXT | Human-readable mode name |
| `mode_category` | TEXT | Mode category grouping |
| `year` | INTEGER | Reference year (2017–2024) |
| `mode_tons` | NUMERIC | Tonnage carried by this mode on this corridor in this year |
| `corridor_total_tons` | NUMERIC | Total tonnage across all modes for this corridor and year |
| `mode_share_pct` | NUMERIC | Percentage of corridor tonnage carried by this mode (0–100) |
| `prev_year_share_pct` | NUMERIC | Prior year mode share percentage for the same corridor/mode |
| `truck_share_decline_flag` | BOOLEAN | True if truck mode share dropped more than 5 percentage points YoY — signals potential truck-to-rail modal shift |
 
**Notes:**
- Rows with `corridor_total_tons = 0` are excluded
- Intra-zonal corridors (origin = destination) are included but filtered in most analyses
- `truck_share_decline_flag` only applies to rows where `mode_name = 'Truck'`
---
 
## `fct_trade_corridor_scorecard`
 
Top 25 trade corridors ranked by a composite score. Updated annually with the most recent year's data.
 
| Column | Type | Description |
|--------|------|-------------|
| `origin_zone` | TEXT | FAF zone code for the origin region |
| `destination_zone` | TEXT | FAF zone code for the destination region |
| `origin_name` | TEXT | Human-readable origin region name |
| `destination_name` | TEXT | Human-readable destination region name |
| `origin_state` | TEXT | Two-letter state code for the origin |
| `destination_state` | TEXT | Two-letter state code for the destination |
| `year` | INTEGER | Reference year (most recent available, currently 2024) |
| `total_tons` | NUMERIC | Total tonnage across all commodities and modes |
| `total_value` | NUMERIC | Total value across all commodities and modes |
| `total_tmiles` | NUMERIC | Total ton-miles across all commodities and modes |
| `mode_count` | INTEGER | Number of distinct transport modes active on this corridor |
| `commodity_count` | INTEGER | Number of distinct commodities shipped on this corridor |
| `avg_yoy_growth_pct` | NUMERIC | Average YoY growth rate across all commodity/mode combinations on this corridor |
| `volume_pct_rank` | NUMERIC | Percentile rank by total tonnage (0–1, higher is better) |
| `value_pct_rank` | NUMERIC | Percentile rank by total value (0–1, higher is better) |
| `growth_pct_rank` | NUMERIC | Percentile rank by average YoY growth (0–1, higher is better) |
| `diversity_pct_rank` | NUMERIC | Percentile rank by mode count (0–1, higher is better) |
| `composite_score` | NUMERIC | Weighted composite score: volume (35%) + value (30%) + growth (25%) + diversity (10%) |
| `corridor_rank` | INTEGER | Final ranking of this corridor (1 = highest composite score) |
 
**Notes:**
- Only inter-zonal corridors are scored (intra-zonal excluded)
- Only the top 25 corridors by composite score are stored
- Scoring weights: volume 35%, value 30%, YoY growth 25%, mode diversity 10%
- Percentile ranks use `percent_rank()` window function — a score of 1.0 means top percentile
---
 
## `fct_disruption_indicators`
 
One row per month. Monthly freight transportation indicators with statistical anomaly detection.
 
| Column | Type | Description |
|--------|------|-------------|
| `obs_date` | DATE | Observation date (first day of the month) |
| `year` | INTEGER | Year of observation |
| `month` | INTEGER | Month of observation (1–12) |
| `tsi_freight` | NUMERIC | BTS Freight Transportation Services Index (base year 2000 = 100) |
| `tsi_freight_pct_change` | NUMERIC | Month-over-month percentage change in freight TSI |
| `truck_vmt` | NUMERIC | Truck vehicle miles traveled (millions) |
| `rail_carloads` | NUMERIC | Rail freight carloads |
| `rail_intermodal` | NUMERIC | Rail intermodal units |
| `petroleum_pipeline` | NUMERIC | Petroleum pipeline throughput |
| `natural_gas_pipeline` | NUMERIC | Natural gas pipeline throughput |
| `waterborne_freight` | NUMERIC | Waterborne freight volume |
| `inventory_to_sales_ratio` | NUMERIC | Ratio of total business inventories to total sales |
| `industrial_production_index` | NUMERIC | Federal Reserve industrial production index |
| `mean_tsi_by_month` | NUMERIC | Average TSI for this calendar month across all years (seasonal baseline) |
| `stddev_tsi_by_month` | NUMERIC | Standard deviation of TSI for this calendar month |
| `avg_vmt_by_month` | NUMERIC | Average truck VMT for this calendar month across all years |
| `stddev_vmt_by_month` | NUMERIC | Standard deviation of truck VMT for this calendar month |
| `tsi_zscore` | NUMERIC | Z-score of TSI relative to seasonal baseline (values beyond ±2 are anomalous) |
| `vmt_zscore` | NUMERIC | Z-score of truck VMT relative to seasonal baseline |
| `is_anomaly` | BOOLEAN | True if either TSI or VMT z-score exceeds ±2 standard deviations |
| `severity` | TEXT | Anomaly severity: `NORMAL`, `MEDIUM` (z > 2), or `HIGH` (z > 3) |
 
**Notes:**
- Source: BTS Transportation Services Index (monthly, seasonally adjusted)
- Z-scores are partitioned by calendar month to account for seasonality
- COVID-19 impact clearly visible: April 2020 VMT z-score = -3.89 (HIGH severity)
- Data covers January 2000 to present
 