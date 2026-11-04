-- ============================================================================
-- SIVA DURGA FINANCE — PRODUCTION DATABASE MIGRATION SCRIPT
-- Modules: Central Banking, Smart Counting, Cashbags, Fleet Telemetry & Sync Feeds
-- Target Database: PostgreSQL 14+ (Production)
-- Idempotency: All statements use IF NOT EXISTS / IF EXISTS safe guards.
-- Transaction: Wrapped in BEGIN ... COMMIT for atomic deployment.
-- Date: November 2026
-- ============================================================================

BEGIN;

-- ============================================================================
-- 0. CORE EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. ALTERATIONS TO EXISTING CORE TABLES
-- ============================================================================

-- 1.1 cashbag_transactions: Allow banking entries without specific village ID
ALTER TABLE cashbag_transactions ALTER COLUMN vid DROP NOT NULL;

-- 1.2 payment: Cash and UPI split balancing
ALTER TABLE payment ADD COLUMN IF NOT EXISTS cash_amount NUMERIC(14, 2);
ALTER TABLE payment ADD COLUMN IF NOT EXISTS upi_amount NUMERIC(14, 2);

-- Update existing payment records to balance cash/upi amounts if NULL
UPDATE payment 
SET cash_amount = amt, upi_amount = 0.00 
WHERE cash_amount IS NULL AND amt IS NOT NULL;

-- Relax payment_type check constraint to permit partial and mixed modes
DO $$
BEGIN
    ALTER TABLE payment DROP CONSTRAINT IF EXISTS payment_payment_type_chk;
    ALTER TABLE payment ADD CONSTRAINT payment_payment_type_chk 
        CHECK (lower(payment_type) = ANY (ARRAY['cash', 'upi', 'partial', 'mixed']));
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- 1.3 closed_cust_payment: Maintain split compatibility on archived accounts
ALTER TABLE closed_cust_payment ADD COLUMN IF NOT EXISTS cash_amount NUMERIC(14, 2);
ALTER TABLE closed_cust_payment ADD COLUMN IF NOT EXISTS upi_amount NUMERIC(14, 2);

UPDATE closed_cust_payment 
SET cash_amount = amt, upi_amount = 0.00 
WHERE cash_amount IS NULL AND amt IS NOT NULL;

-- ============================================================================
-- 2. CENTRAL BANKING SYSTEM (15 TABLES)
-- ============================================================================

-- 2.1 INVESTORS: Master registry of external & internal equity investors
CREATE TABLE IF NOT EXISTS investors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_code VARCHAR(30) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(100),
    aadhaar_number VARCHAR(12),
    pan_number VARCHAR(10),
    address TEXT,
    nominee_name VARCHAR(150),
    nominee_relation VARCHAR(50),
    nominee_phone VARCHAR(15),
    global_share_pct NUMERIC(6,3) DEFAULT 0.000,
    linked_chit_member_id UUID REFERENCES chit_members(id) ON DELETE SET NULL,
    username VARCHAR(50) UNIQUE,
    password_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.2 INVESTOR_TRANSACTIONS: Master audit ledger for investor central capital flows
CREATE TABLE IF NOT EXISTS investor_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE RESTRICT,
    txn_type VARCHAR(30) NOT NULL, -- 'DEPOSIT', 'IDLE_WITHDRAWAL', 'CAPITAL_DEPLOYED', 'PRINCIPAL_RETURN', 'INTEREST_RETURN', 'PROFIT_PAYOUT', 'EXPENSE_DRAW'
    payment_mode VARCHAR(10) NOT NULL, -- 'CASH', 'UPI'
    amount NUMERIC(14,2) NOT NULL,
    txn_date DATE NOT NULL,
    reference_id UUID,
    notes TEXT,
    is_backdated BOOLEAN DEFAULT FALSE,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.3 VILLAGE_GROUPS: Permanent Village Group Banks (Route Banks)
CREATE TABLE IF NOT EXISTS village_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_code VARCHAR(50) UNIQUE NOT NULL,
    group_name VARCHAR(150) NOT NULL,
    emp1_id INT REFERENCES employee(eid) ON DELETE SET NULL,
    emp2_id INT REFERENCES employee(eid) ON DELETE SET NULL,
    collection_days_per_week INT NOT NULL CHECK (collection_days_per_week BETWEEN 1 AND 7),
    assigned_villages TEXT,
    assigned_village_codes TEXT[],
    status VARCHAR(20) DEFAULT 'ACTIVE',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Link cashbag_transactions to village_groups
ALTER TABLE cashbag_transactions 
    ADD COLUMN IF NOT EXISTS group_id UUID REFERENCES village_groups(id) ON DELETE SET NULL;

-- 2.4 VILLAGE_GROUP_OPENINGS: Historical opening balances for existing groups
CREATE TABLE IF NOT EXISTS village_group_openings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID UNIQUE NOT NULL REFERENCES village_groups(id) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    initial_invested_principal NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    accrued_interest_to_date NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    profit_in_circulation NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    cashbag_opening_cash NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    cashbag_opening_upi NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.5 INVESTOR_GROUP_SHARES: Per-village group ownership overrides (sums to 100%)
CREATE TABLE IF NOT EXISTS investor_group_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES village_groups(id) ON DELETE CASCADE,
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE CASCADE,
    share_pct NUMERIC(6,3) NOT NULL CHECK (share_pct >= 0 AND share_pct <= 100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, investor_id)
);

-- 2.6 GROUP_CAPITAL_ALLOCATIONS: Capital deployed into Village Group Banks
CREATE TABLE IF NOT EXISTS group_capital_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES village_groups(id) ON DELETE RESTRICT,
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE RESTRICT,
    amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,
    allocation_date DATE NOT NULL,
    interest_rate NUMERIC(5,2) DEFAULT 24.00,
    cashbag_txn_id INT REFERENCES cashbag_transactions(id) ON DELETE SET NULL,
    is_backdated BOOLEAN DEFAULT FALSE,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.7 GROUP_WITHDRAWAL_LOGS: Waterfall withdrawals from Village Groups
CREATE TABLE IF NOT EXISTS group_withdrawal_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES village_groups(id) ON DELETE RESTRICT,
    total_withdrawn NUMERIC(14,2) NOT NULL,
    principal_portion NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    interest_portion NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    profit_portion NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    payment_mode VARCHAR(10) NOT NULL,
    withdrawal_date DATE NOT NULL,
    admin_auth_confirmed BOOLEAN DEFAULT TRUE,
    is_backdated BOOLEAN DEFAULT FALSE,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.8 GROUP_WITHDRAWAL_ALLOCATIONS: Itemized investor distribution of withdrawals
CREATE TABLE IF NOT EXISTS group_withdrawal_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    withdrawal_id UUID NOT NULL REFERENCES group_withdrawal_logs(id) ON DELETE CASCADE,
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE RESTRICT,
    component_type VARCHAR(20) NOT NULL, -- 'PRINCIPAL', 'INTEREST', 'PROFIT'
    amount NUMERIC(14,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.9 ANNUAL_EXPENSE_SETTLEMENTS: Yearly expense settlements across Village Groups
CREATE TABLE IF NOT EXISTS annual_expense_settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settlement_year VARCHAR(20) NOT NULL,
    settlement_date DATE NOT NULL,
    total_expenses NUMERIC(14,2) NOT NULL,
    total_days INT NOT NULL,
    executed_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.10 CENTRAL_OFFICE_EXPENSES: Central operational expenses (rent, salaries, utilities)
CREATE TABLE IF NOT EXISTS central_office_expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expense_category VARCHAR(50) NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,
    expense_date DATE NOT NULL,
    description TEXT,
    reallocated_annual_id UUID REFERENCES annual_expense_settlements(id) ON DELETE SET NULL,
    is_settled BOOLEAN DEFAULT FALSE,
    is_backdated BOOLEAN DEFAULT FALSE,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.11 GROUP_EXPENSE_ALLOCATIONS: Individual village group share of annual settlement
CREATE TABLE IF NOT EXISTS group_expense_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settlement_id UUID NOT NULL REFERENCES annual_expense_settlements(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES village_groups(id) ON DELETE RESTRICT,
    group_days INT NOT NULL,
    allocated_amount NUMERIC(14,2) NOT NULL,
    cashbag_txn_id INT REFERENCES cashbag_transactions(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.12 INVESTOR_PERSONAL_EXPENSES: Personal drawings & expenses debited to investors
CREATE TABLE IF NOT EXISTS investor_personal_expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE RESTRICT,
    amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,
    expense_date DATE NOT NULL,
    item_description TEXT NOT NULL,
    receipt_no VARCHAR(50),
    is_settled BOOLEAN DEFAULT FALSE,
    settled_at TIMESTAMPTZ,
    settled_by VARCHAR(50),
    settlement_mode VARCHAR(20),
    settlement_ref VARCHAR(100),
    settlement_notes TEXT,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.13 DIRECT_INDIVIDUAL_LOANS: External loans funded directly from Central Bank
CREATE TABLE IF NOT EXISTS direct_individual_loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    borrower_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    aadhaar_number VARCHAR(12),
    principal_amount NUMERIC(14,2) NOT NULL,
    annual_interest_rate NUMERIC(5,2) NOT NULL,
    disbursal_date DATE NOT NULL,
    due_date DATE,
    repayment_type VARCHAR(20) NOT NULL, -- 'BULLET', 'MONTHLY_INTEREST', 'INSTALLMENT'
    revenue_allocation VARCHAR(20) NOT NULL, -- 'POOLED', 'ATTRIBUTED'
    funding_investor_id UUID REFERENCES investors(id) ON DELETE SET NULL,
    payment_mode VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    notes TEXT,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.14 DIRECT_LOAN_REPAYMENTS: Installment collections on direct individual loans
CREATE TABLE IF NOT EXISTS direct_loan_repayments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES direct_individual_loans(id) ON DELETE RESTRICT,
    repayment_date DATE NOT NULL,
    principal_amount NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    interest_amount NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.15 CHIT_INTERBANK_TRANSFERS: Liquidity bridge between Chit Fund and Central Bank
CREATE TABLE IF NOT EXISTS chit_interbank_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    direction VARCHAR(30) NOT NULL, -- 'CHIT_TO_INVESTMENT', 'INVESTMENT_TO_CHIT'
    chit_group_id UUID REFERENCES chit_groups(id) ON DELETE SET NULL,
    amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,
    transfer_date DATE NOT NULL,
    reason TEXT NOT NULL,
    admin_auth_confirmed BOOLEAN DEFAULT TRUE,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 3. SMART COUNTING & VILLAGE CASHBAGS SYSTEM
-- ============================================================================

-- 3.1 VILLAGE_CASHBAGS: Dynamic multi-cashbag routes per employee pair
CREATE TABLE IF NOT EXISTS village_cashbags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    emp1 INT NOT NULL,
    emp2 INT,
    name VARCHAR(150) NOT NULL,
    village_codes TEXT[] NOT NULL DEFAULT '{}',
    week_ending_day INT DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_village_cashbags_emp ON village_cashbags(emp1, emp2);

-- 3.2 MOBILE OFFLINE FEED & GUARDRAIL TABLES
CREATE TABLE IF NOT EXISTS customer_feed_edits (
    edit_id SERIAL PRIMARY KEY,
    local_uuid TEXT NOT NULL,
    edited_payload JSONB NOT NULL,
    eid INTEGER,
    vid INTEGER,
    edit_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_feed_edits (
    edit_id SERIAL PRIMARY KEY,
    local_uuid TEXT NOT NULL,
    edited_payload JSONB NOT NULL,
    eid INTEGER,
    vid INTEGER,
    edit_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feed_rejections (
    rejection_id SERIAL PRIMARY KEY,
    feed_type TEXT NOT NULL,
    local_uuid TEXT,
    ano INTEGER,
    vid INTEGER,
    eid INTEGER,
    action_type TEXT DEFAULT 'rejected_deleted',
    deleted_by TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feed_rejections_vid ON feed_rejections (vid);
CREATE INDEX IF NOT EXISTS idx_feed_rejections_uuid ON feed_rejections (local_uuid);

CREATE TABLE IF NOT EXISTS customer_docs_feed (
    docs_feed_id BIGSERIAL PRIMARY KEY,
    local_uuid TEXT UNIQUE,
    ano INT,
    vid INT,
    eid INT,
    docs_payload JSONB,
    sync_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS account_closure_feed (
    feed_id BIGSERIAL PRIMARY KEY,
    local_uuid TEXT UNIQUE,
    device_id TEXT,
    eid INTEGER,
    vid INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    closure_date DATE,
    closure_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 4. FLEET TELEMETRY & HARDWARE SECURITY
-- ============================================================================

-- 4.1 user_devices: Multi-device registry & live telemetry state
CREATE TABLE IF NOT EXISTS user_devices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    device_id TEXT NOT NULL,
    device_model TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_active TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_devices 
    ADD COLUMN IF NOT EXISTS device_model TEXT,
    ADD COLUMN IF NOT EXISTS latest_latitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS latest_longitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS latest_speed REAL DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS latest_heading REAL DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS latest_accuracy REAL,
    ADD COLUMN IF NOT EXISTS latest_battery_pct SMALLINT,
    ADD COLUMN IF NOT EXISTS is_charging BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS gps_status VARCHAR(20) DEFAULT 'active';

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_devices_user_device 
    ON user_devices (user_id, device_id);

-- 4.2 user_locations: High-frequency GPS breadcrumbs (10-day retention)
CREATE TABLE IF NOT EXISTS user_locations (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(64) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    accuracy REAL,
    speed REAL DEFAULT 0.0,
    heading REAL DEFAULT 0.0,
    battery_pct SMALLINT,
    is_charging BOOLEAN DEFAULT FALSE,
    activity_type VARCHAR(20) DEFAULT 'unknown',
    recorded_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_locations_user_recorded 
    ON user_locations (user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_locations_recorded_at 
    ON user_locations (recorded_at);

-- 4.3 user_daily_trips: Permanent daily aggregated journey rollups
CREATE TABLE IF NOT EXISTS user_daily_trips (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trip_date DATE NOT NULL,
    total_distance_km NUMERIC(8, 2) DEFAULT 0.00,
    travel_minutes INTEGER DEFAULT 0,
    stop_minutes INTEGER DEFAULT 0,
    stop_count INTEGER DEFAULT 0,
    first_ping_at TIMESTAMPTZ,
    last_ping_at TIMESTAMPTZ,
    battery_start_pct SMALLINT,
    battery_end_pct SMALLINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, trip_date)
);

CREATE INDEX IF NOT EXISTS idx_user_daily_trips_user_date 
    ON user_daily_trips (user_id, trip_date DESC);

-- 4.4 device_wipe_audit: Remote security wipe & lock audit trail
CREATE TABLE IF NOT EXISTS device_wipe_audit (
    id SERIAL PRIMARY KEY,
    user_id INT,
    device_id TEXT NOT NULL,
    reason TEXT,
    ip_address TEXT,
    wiped_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 5. UNIFIED REVENUE & PAYMENT VIEWS
-- ============================================================================

-- 5.1 v_all_payments: 3-tier union of active, closed, and historic payments
CREATE OR REPLACE VIEW v_all_payments AS
 SELECT cll.ucid,
    p.pid,
    p.cid,
    p.vid,
    p.ano,
    p.eid,
    p.payment_date,
    p.amt,
    p.payment_type,
    p.cash_amount,
    p.upi_amount,
    p.created_at,
    p.updated_at,
    'active'::text AS record_tier
   FROM payment p
     LEFT JOIN customer_loan_link cll ON p.cid = cll.cid
UNION ALL
 SELECT cll.ucid,
    ccp.pid,
    ccp.cid,
    ccp.vid,
    ccp.ano,
    ccp.eid,
    ccp.payment_date,
    ccp.amt,
    'cash'::character varying(10) AS payment_type,
    ccp.amt AS cash_amount,
    0.00::numeric(14,2) AS upi_amount,
    ccp.created_at,
    NULL::timestamp with time zone AS updated_at,
    'closed'::text AS record_tier
   FROM closed_cust_payment ccp
     LEFT JOIN customer_loan_link cll ON ccp.cid = cll.cid
UNION ALL
 SELECT cll.ucid,
    hpd.pid,
    hpd.cid,
    hpd.vid,
    hpd.ano,
    hpd.eid,
    hpd.payment_date,
    hpd.amount::numeric(14,2) AS amt,
    'cash'::character varying(10) AS payment_type,
    hpd.amount::numeric(14,2) AS cash_amount,
    0.00::numeric(14,2) AS upi_amount,
    hpd.created_at::timestamp with time zone AS created_at,
    NULL::timestamp with time zone AS updated_at,
    'historic'::text AS record_tier
   FROM historic_payment_data hpd
     LEFT JOIN customer_loan_link cll ON hpd.cid = cll.cid;

-- 5.2 v_all_customers: Unified customer view across active, closed, and historic
CREATE OR REPLACE VIEW v_all_customers AS
 SELECT cll.ucid,
    cll.cycle_number,
    c.cid,
    c.ano,
    c.name,
    c.vid,
    c.eid,
    c.start_date,
    c.end_date,
    c.total_amount,
    c.paid_amount,
    c.balance_amount,
    c.installment_amount,
    c.type,
    c.period,
    c.pano,
    c.created_at,
    c.updated_at,
    NULL::timestamp with time zone AS closed_at,
    NULL::integer AS closed_by,
    c.aadhaar_number,
    c.phone_number,
    c.notes,
    c.latitude,
    c.longitude,
    c.status,
    c.customer_rating,
    c.final_frozen_rating,
    c.final_risk_level,
    c.freeze_date,
    c.base_amount,
    c.cutting_amount,
    c.interest_amount,
    c.payment_type,
    c.interest_discount,
    'active'::text AS record_tier
   FROM customer c
     LEFT JOIN customer_loan_link cll ON c.cid = cll.cid
UNION ALL
 SELECT cll.ucid,
    cll.cycle_number,
    cc.cid,
    cc.ano,
    cc.name,
    cc.vid,
    cc.eid,
    cc.start_date,
    cc.end_date,
    cc.total_amount,
    cc.paid_amount,
    cc.balance_amount,
    cc.installment_amount,
    cc.type,
    cc.period,
    cc.pano,
    cc.created_at,
    NULL::timestamp with time zone AS updated_at,
    cc.closed_at,
    cc.closed_by,
    cc.aadhaar_number,
    cc.phone_number,
    cc.notes,
    cc.latitude,
    cc.longitude,
    cc.status,
    cc.customer_rating,
    cc.final_frozen_rating,
    cc.final_risk_level,
    cc.freeze_date,
    cc.base_amount,
    cc.cutting_amount,
    cc.interest_amount,
    cc.payment_type,
    cc.interest_discount,
    'closed'::text AS record_tier
   FROM closed_cust_account cc
     LEFT JOIN customer_loan_link cll ON cc.cid = cll.cid
UNION ALL
 SELECT cll.ucid,
    COALESCE(cll.cycle_number, 1) AS cycle_number,
    hc.cid,
    hc.ano,
    hc.name,
    hc.vid,
    hc.eid,
    hc.start_date,
    hc.end_date,
    hc.total_amount,
    hc.paid_amount,
    hc.balance_amount,
    hc.installment_amount,
    hc.type,
    hc.period,
    hc.pano,
    hc.created_at,
    NULL::timestamp with time zone AS updated_at,
    hc.closed_at,
    NULL::integer AS closed_by,
    hc.aadhaar_number,
    hc.phone_number,
    hc.notes,
    hc.latitude,
    hc.longitude,
    hc.status,
    hc.customer_rating,
    hc.final_frozen_rating,
    hc.final_risk_level,
    hc.freeze_date,
    hc.base_amount,
    hc.cutting_amount,
    hc.interest_amount,
    hc.payment_type,
    hc.interest_discount,
    'historic'::text AS record_tier
   FROM historic_customer_data hc
     LEFT JOIN customer_loan_link cll ON hc.cid = cll.cid;

-- ============================================================================
-- 6. PERFORMANCE & AUDIT INDEXES
-- ============================================================================

-- Ledger & allocation performance
CREATE INDEX IF NOT EXISTS idx_investor_txns_investor_date ON investor_transactions (investor_id, txn_date);
CREATE INDEX IF NOT EXISTS idx_group_cap_alloc_group_date ON group_capital_allocations (group_id, allocation_date);
CREATE INDEX IF NOT EXISTS idx_group_withdr_logs_group_date ON group_withdrawal_logs (group_id, withdrawal_date);
CREATE INDEX IF NOT EXISTS idx_investor_pers_exp_inv_date ON investor_personal_expenses (investor_id, expense_date);
CREATE INDEX IF NOT EXISTS idx_direct_loan_repay_loan_date ON direct_loan_repayments (loan_id, repayment_date);

-- Audit exclusion and reversal indexes
CREATE INDEX IF NOT EXISTS idx_investor_txns_reversed ON investor_transactions (is_reversed);
CREATE INDEX IF NOT EXISTS idx_group_cap_alloc_reversed ON group_capital_allocations (is_reversed);
CREATE INDEX IF NOT EXISTS idx_group_withdr_logs_reversed ON group_withdrawal_logs (is_reversed);
CREATE INDEX IF NOT EXISTS idx_central_off_exp_reversed ON central_office_expenses (is_reversed);
CREATE INDEX IF NOT EXISTS idx_investor_pers_exp_reversed ON investor_personal_expenses (is_reversed);
CREATE INDEX IF NOT EXISTS idx_direct_loans_reversed ON direct_individual_loans (is_reversed);
CREATE INDEX IF NOT EXISTS idx_direct_loan_repay_reversed ON direct_loan_repayments (is_reversed);
CREATE INDEX IF NOT EXISTS idx_chit_interbank_reversed ON chit_interbank_transfers (is_reversed);

-- Foreign key & fast filter indexes
CREATE INDEX IF NOT EXISTS idx_investors_code ON investors (investor_code);
CREATE INDEX IF NOT EXISTS idx_investors_phone ON investors (phone_number);
CREATE INDEX IF NOT EXISTS idx_investors_active ON investors (is_active);
CREATE INDEX IF NOT EXISTS idx_village_groups_code ON village_groups (group_code);
CREATE INDEX IF NOT EXISTS idx_village_groups_status ON village_groups (status);
CREATE INDEX IF NOT EXISTS idx_investor_shares_group ON investor_group_shares (group_id);
CREATE INDEX IF NOT EXISTS idx_investor_shares_investor ON investor_group_shares (investor_id);
CREATE INDEX IF NOT EXISTS idx_group_cap_alloc_investor ON group_capital_allocations (investor_id);
CREATE INDEX IF NOT EXISTS idx_group_withdr_alloc_withdr ON group_withdrawal_allocations (withdrawal_id);
CREATE INDEX IF NOT EXISTS idx_group_withdr_alloc_investor ON group_withdrawal_allocations (investor_id);
CREATE INDEX IF NOT EXISTS idx_central_off_exp_date ON central_office_expenses (expense_date);
CREATE INDEX IF NOT EXISTS idx_central_off_exp_settled ON central_office_expenses (is_settled);
CREATE INDEX IF NOT EXISTS idx_group_exp_alloc_settlement ON group_expense_allocations (settlement_id);
CREATE INDEX IF NOT EXISTS idx_group_exp_alloc_group ON group_expense_allocations (group_id);
CREATE INDEX IF NOT EXISTS idx_direct_loans_status ON direct_individual_loans (status);
CREATE INDEX IF NOT EXISTS idx_direct_loans_investor ON direct_individual_loans (funding_investor_id);
CREATE INDEX IF NOT EXISTS idx_chit_interbank_date ON chit_interbank_transfers (transfer_date);
CREATE INDEX IF NOT EXISTS idx_chit_interbank_group ON chit_interbank_transfers (chit_group_id);

-- ============================================================================
-- 7. CLEANUP OBSOLETE HARDWARE DUPLICATES
-- ============================================================================
UPDATE user_devices
SET is_active = FALSE
WHERE id IN (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY user_id, COALESCE(device_model, 'unknown')
                   ORDER BY last_active DESC NULLS LAST, id DESC
               ) as rn
        FROM user_devices
        WHERE is_active = TRUE AND device_id != 'PENDING'
    ) sub
    WHERE rn > 1
);

COMMIT;
-- ============================================================================
-- END OF SCRIPT: Migration Complete and Committed.
-- ============================================================================
