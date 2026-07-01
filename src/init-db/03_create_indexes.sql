-- Speed up fct_corridor_flows joins
CREATE INDEX IF NOT EXISTS idx_faf_long_origin 
    ON silver.stg_faf_shipments_long (origin_zone);

CREATE INDEX IF NOT EXISTS idx_faf_long_dest 
    ON silver.stg_faf_shipments_long (destination_zone);

CREATE INDEX IF NOT EXISTS idx_faf_long_commodity 
    ON silver.stg_faf_shipments_long (commodity_code);

CREATE INDEX IF NOT EXISTS idx_faf_long_mode 
    ON silver.stg_faf_shipments_long (mode_code);

CREATE INDEX IF NOT EXISTS idx_faf_long_year 
    ON silver.stg_faf_shipments_long (year);

-- Speed up gold layer queries
CREATE INDEX IF NOT EXISTS idx_corridor_flows_origin 
    ON gold.fct_corridor_flows (origin_zone);

CREATE INDEX IF NOT EXISTS idx_corridor_flows_state 
    ON gold.fct_corridor_flows (origin_state, destination_state);

CREATE INDEX IF NOT EXISTS idx_corridor_flows_commodity 
    ON gold.fct_corridor_flows (commodity_category);

CREATE INDEX IF NOT EXISTS idx_corridor_flows_year 
    ON gold.fct_corridor_flows (year);