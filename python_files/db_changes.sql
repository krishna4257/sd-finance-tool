-- =============================================================================
-- DATABASE MIGRATIONS LOG (SD Finance Tool)
-- =============================================================================
-- Execute these SQL statements on your PostgreSQL database to align the schema
-- with the application's updates.
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- Change #1
-- Table: village
-- Description: Add latitude and longitude columns to support geolocating villages on the dashboard map.
-- -----------------------------------------------------------------------------
ALTER TABLE village ADD COLUMN latitude NUMERIC;
ALTER TABLE village ADD COLUMN longitude NUMERIC;

-- -----------------------------------------------------------------------------
-- Change #2
-- Table: historic_customer_data
-- Description: Create historical customer records table to hold archived profiles.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historic_customer_data (
    cid bigint PRIMARY KEY,
    ano integer,
    name text,
    vid integer,
    start_date date,
    end_date date,
    total_amount numeric,
    paid_amount numeric,
    balance_amount numeric,
    installment_amount numeric,
    type character(1),
    period integer,
    pano text,
    created_at timestamp with time zone,
    aadhaar_number text,
    notes text,
    latitude numeric,
    longitude numeric,
    eid integer,
    status text,
    closed_at timestamp with time zone,
    phone_number text,
    customer_rating numeric,
    final_frozen_rating numeric,
    final_risk_level text,
    freeze_date timestamp with time zone,
    base_amount numeric,
    cutting_amount numeric,
    interest_amount numeric
);

-- -----------------------------------------------------------------------------
-- Change #3
-- Table: historic_payment_data
-- Description: Add cid column to reference the historic customer records.
-- -----------------------------------------------------------------------------
ALTER TABLE historic_payment_data ADD COLUMN cid bigint;

-- -----------------------------------------------------------------------------
-- Change #4
-- Indexes
-- Description: Create indexes on payment and account tables to optimize query speeds.
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_historic_payment_vid_ano ON historic_payment_data (vid, ano);
CREATE INDEX IF NOT EXISTS idx_closed_cust_payment_vid_ano ON closed_cust_payment (vid, ano);
CREATE INDEX IF NOT EXISTS idx_payment_cid_date ON payment (cid, payment_date);
CREATE INDEX IF NOT EXISTS idx_closed_payment_cid_date ON closed_cust_payment (cid, payment_date);
CREATE INDEX IF NOT EXISTS idx_historic_payment_cid_date ON historic_payment_data (cid, payment_date);

-- -----------------------------------------------------------------------------
-- Change #5
-- Table: village_health_cache
-- Description: Create cache table for pre-computed Village Health History snapshots.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS village_health_cache (
    vid INT NOT NULL,
    view VARCHAR(20) NOT NULL,
    sub_view VARCHAR(20) NOT NULL,
    time_range VARCHAR(20) NOT NULL,
    date_key DATE NOT NULL,
    health_score NUMERIC(5, 2) NOT NULL,
    metrics JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (vid, view, sub_view, time_range, date_key)
);

-- -----------------------------------------------------------------------------
-- Change #6
-- Table: employee
-- Description: Standardize employee levels to lowercase to prevent case-sensitive mismatches.
-- -----------------------------------------------------------------------------
UPDATE employee SET level = LOWER(TRIM(level));

