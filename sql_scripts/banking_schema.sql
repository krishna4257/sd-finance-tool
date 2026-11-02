-- ============================================================================
-- SIVA DURGA FINANCE — HIERARCHICAL BANKING SYSTEM
-- Database Migration Script: Banking System DDL & Performance Indexes
-- Schema Target: PostgreSQL (Replica / Production)
-- Date: October 2026
-- ============================================================================

-- Ensure required extensions are active for UUID generation and crypto
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Allow cashbag_transactions to record central office / banking adjustments without a specific village ID
ALTER TABLE cashbag_transactions ALTER COLUMN vid DROP NOT NULL;

-- ============================================================================
-- 1. INVESTORS
-- Core profile, KYC registry, and identity linkage for all 100+ individual investors
-- ============================================================================
CREATE TABLE IF NOT EXISTS investors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_code VARCHAR(30) UNIQUE NOT NULL,            -- e.g. 'INV-001'
    full_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(100),
    aadhaar_number VARCHAR(12),
    pan_number VARCHAR(10),
    address TEXT,
    nominee_name VARCHAR(150),
    nominee_relation VARCHAR(50),
    nominee_phone VARCHAR(15),
    global_share_pct NUMERIC(6,3) DEFAULT 0.000,          -- Default global ownership % (e.g. 5.500)
    linked_chit_member_id UUID REFERENCES chit_members(id) ON DELETE SET NULL, -- Link to Chit Member
    username VARCHAR(50) UNIQUE,                          -- Investor portal authentication
    password_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 2. INVESTOR_TRANSACTIONS
-- Master audit ledger for all capital movements into and out of investor central accounts
-- ============================================================================
CREATE TABLE IF NOT EXISTS investor_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE RESTRICT,
    txn_type VARCHAR(30) NOT NULL,                        -- 'DEPOSIT', 'IDLE_WITHDRAWAL', 'CAPITAL_DEPLOYED', 'PRINCIPAL_RETURN', 'INTEREST_RETURN', 'PROFIT_PAYOUT', 'EXPENSE_DRAW'
    payment_mode VARCHAR(10) NOT NULL,                    -- 'CASH', 'UPI'
    amount NUMERIC(14,2) NOT NULL,
    txn_date DATE NOT NULL,                               -- Effective transaction date
    reference_id UUID,                                    -- Corresponds to allocation/withdrawal/loan ID
    notes TEXT,
    is_backdated BOOLEAN DEFAULT FALSE,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 3. VILLAGE_GROUPS
-- Permanent registry of Village Group Banks (Route Banks), decoupled from staff assignments
-- ============================================================================
CREATE TABLE IF NOT EXISTS village_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_code VARCHAR(50) UNIQUE NOT NULL,               -- e.g. 'VG-001', 'ROUTE-TANUKU'
    group_name VARCHAR(150) NOT NULL,
    emp1_id INT REFERENCES employee(eid) ON DELETE SET NULL,
    emp2_id INT REFERENCES employee(eid) ON DELETE SET NULL,
    collection_days_per_week INT NOT NULL CHECK (collection_days_per_week BETWEEN 1 AND 7),
    assigned_villages TEXT,
    assigned_village_codes TEXT[],
    status VARCHAR(20) DEFAULT 'ACTIVE',                  -- 'ACTIVE', 'INACTIVE', 'CLOSED'
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE village_groups ADD COLUMN IF NOT EXISTS assigned_villages TEXT;
ALTER TABLE village_groups ADD COLUMN IF NOT EXISTS assigned_village_codes TEXT[];
ALTER TABLE cashbag_transactions ADD COLUMN IF NOT EXISTS group_id UUID REFERENCES village_groups(id) ON DELETE SET NULL;

-- ============================================================================
-- 4. VILLAGE_GROUP_OPENINGS
-- Opening balance migration records for existing groups operating 5-10 years
-- ============================================================================
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

-- ============================================================================
-- 5. INVESTOR_GROUP_SHARES
-- Per-village group ownership shareholding overrides (sums to 100% per group)
-- ============================================================================
CREATE TABLE IF NOT EXISTS investor_group_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES village_groups(id) ON DELETE CASCADE,
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE CASCADE,
    share_pct NUMERIC(6,3) NOT NULL CHECK (share_pct >= 0 AND share_pct <= 100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, investor_id)
);

-- ============================================================================
-- 6. GROUP_CAPITAL_ALLOCATIONS
-- Tracks capital deployed from Investment Pool into a Village Group's Cashbag
-- ============================================================================
CREATE TABLE IF NOT EXISTS group_capital_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES village_groups(id) ON DELETE RESTRICT,
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE RESTRICT, -- Actual funding investor
    amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,                    -- 'CASH', 'UPI'
    allocation_date DATE NOT NULL,
    interest_rate NUMERIC(5,2) DEFAULT 24.00,             -- Universal 24% annual compounding rate
    cashbag_txn_id INT REFERENCES cashbag_transactions(id) ON DELETE SET NULL, -- Linked row in cashbag_transactions
    is_backdated BOOLEAN DEFAULT FALSE,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 7. GROUP_WITHDRAWAL_LOGS
-- Records withdrawals from Village Groups with waterfall breakdown (Principal -> Interest -> Profit)
-- ============================================================================
CREATE TABLE IF NOT EXISTS group_withdrawal_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES village_groups(id) ON DELETE RESTRICT,
    total_withdrawn NUMERIC(14,2) NOT NULL,
    principal_portion NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    interest_portion NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    profit_portion NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    payment_mode VARCHAR(10) NOT NULL,                    -- 'CASH', 'UPI'
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

-- ============================================================================
-- 8. GROUP_WITHDRAWAL_ALLOCATIONS
-- Itemized credit distribution of withdrawn funds to individual investor accounts
-- ============================================================================
CREATE TABLE IF NOT EXISTS group_withdrawal_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    withdrawal_id UUID NOT NULL REFERENCES group_withdrawal_logs(id) ON DELETE CASCADE,
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE RESTRICT,
    component_type VARCHAR(20) NOT NULL,                  -- 'PRINCIPAL', 'INTEREST', 'PROFIT'
    amount NUMERIC(14,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 9. ANNUAL_EXPENSE_SETTLEMENTS
-- Annual execution records reallocating accumulated office expenses across Village Groups
-- ============================================================================
CREATE TABLE IF NOT EXISTS annual_expense_settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settlement_year VARCHAR(20) NOT NULL,                 -- e.g. 'FY-2025-26'
    settlement_date DATE NOT NULL,
    total_expenses NUMERIC(14,2) NOT NULL,
    total_days INT NOT NULL,
    executed_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 10. CENTRAL_OFFICE_EXPENSES
-- Operating expenses paid out of the central Investment Pool (rent, electricity, salaries)
-- ============================================================================
CREATE TABLE IF NOT EXISTS central_office_expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expense_category VARCHAR(50) NOT NULL,                -- 'RENT', 'ELECTRICITY', 'SALARY', 'STATIONERY', 'SOFTWARE', 'MAINTENANCE', 'OTHER'
    amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,                    -- 'CASH', 'UPI'
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

-- ============================================================================
-- 11. GROUP_EXPENSE_ALLOCATIONS
-- Breakdown of an annual expense settlement applied to each individual Village Group
-- ============================================================================
CREATE TABLE IF NOT EXISTS group_expense_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settlement_id UUID NOT NULL REFERENCES annual_expense_settlements(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES village_groups(id) ON DELETE RESTRICT,
    group_days INT NOT NULL,
    allocated_amount NUMERIC(14,2) NOT NULL,
    cashbag_txn_id INT REFERENCES cashbag_transactions(id) ON DELETE SET NULL, -- Linked EXPENSE entry in cashbag_transactions
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 12. INVESTOR_PERSONAL_EXPENSES
-- Personal expenses / drawings booked on behalf of an investor (debited from idle cash)
-- ============================================================================
CREATE TABLE IF NOT EXISTS investor_personal_expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investor_id UUID NOT NULL REFERENCES investors(id) ON DELETE RESTRICT,
    amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,                    -- 'CASH', 'UPI'
    expense_date DATE NOT NULL,
    item_description TEXT NOT NULL,                       -- e.g. 'Amazon order courier delivery'
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

ALTER TABLE investor_personal_expenses ADD COLUMN IF NOT EXISTS is_settled BOOLEAN DEFAULT FALSE;
ALTER TABLE investor_personal_expenses ADD COLUMN IF NOT EXISTS settled_at TIMESTAMPTZ;
ALTER TABLE investor_personal_expenses ADD COLUMN IF NOT EXISTS settled_by VARCHAR(50);
ALTER TABLE investor_personal_expenses ADD COLUMN IF NOT EXISTS settlement_mode VARCHAR(20);
ALTER TABLE investor_personal_expenses ADD COLUMN IF NOT EXISTS settlement_ref VARCHAR(100);
ALTER TABLE investor_personal_expenses ADD COLUMN IF NOT EXISTS settlement_notes TEXT;

-- ============================================================================
-- 13. DIRECT_INDIVIDUAL_LOANS
-- Loans issued directly from the central Investment Pool to outside borrowers
-- ============================================================================
CREATE TABLE IF NOT EXISTS direct_individual_loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    borrower_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    aadhaar_number VARCHAR(12),
    principal_amount NUMERIC(14,2) NOT NULL,
    annual_interest_rate NUMERIC(5,2) NOT NULL,
    disbursal_date DATE NOT NULL,
    due_date DATE,
    repayment_type VARCHAR(20) NOT NULL,                  -- 'BULLET', 'MONTHLY_INTEREST', 'INSTALLMENT'
    revenue_allocation VARCHAR(20) NOT NULL,              -- 'POOLED', 'ATTRIBUTED'
    funding_investor_id UUID REFERENCES investors(id) ON DELETE SET NULL, -- If revenue_allocation is ATTRIBUTED
    payment_mode VARCHAR(10) NOT NULL,                    -- 'CASH', 'UPI'
    status VARCHAR(20) DEFAULT 'ACTIVE',                  -- 'ACTIVE', 'SETTLED', 'DEFAULTED'
    notes TEXT,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 14. DIRECT_LOAN_REPAYMENTS
-- Repayment installments collected against direct individual loans
-- ============================================================================
CREATE TABLE IF NOT EXISTS direct_loan_repayments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES direct_individual_loans(id) ON DELETE RESTRICT,
    repayment_date DATE NOT NULL,
    principal_amount NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    interest_amount NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,                    -- 'CASH', 'UPI'
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 15. CHIT_INTERBANK_TRANSFERS
-- Two-way liquidity bridge movements between Chit Fund Bank and Investment Bank
-- ============================================================================
CREATE TABLE IF NOT EXISTS chit_interbank_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    direction VARCHAR(30) NOT NULL,                       -- 'CHIT_TO_INVESTMENT', 'INVESTMENT_TO_CHIT'
    chit_group_id UUID REFERENCES chit_groups(id) ON DELETE SET NULL,
    amount NUMERIC(14,2) NOT NULL,
    payment_mode VARCHAR(10) NOT NULL,                    -- 'CASH', 'UPI'
    transfer_date DATE NOT NULL,
    reason TEXT NOT NULL,                                 -- e.g. 'Foreman commission surplus transfer', 'Pot deficit funding'
    admin_auth_confirmed BOOLEAN DEFAULT TRUE,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(50),
    reversal_reason TEXT,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- PERFORMANCE & AUDIT LOOKUP INDEXES
-- ============================================================================

-- 1. Composite lookup indexes for high-frequency ledger and allocation queries
CREATE INDEX IF NOT EXISTS idx_investor_txns_investor_date 
    ON investor_transactions (investor_id, txn_date);

CREATE INDEX IF NOT EXISTS idx_group_cap_alloc_group_date 
    ON group_capital_allocations (group_id, allocation_date);

CREATE INDEX IF NOT EXISTS idx_group_withdr_logs_group_date 
    ON group_withdrawal_logs (group_id, withdrawal_date);

CREATE INDEX IF NOT EXISTS idx_investor_pers_exp_inv_date 
    ON investor_personal_expenses (investor_id, expense_date);

CREATE INDEX IF NOT EXISTS idx_direct_loan_repay_loan_date 
    ON direct_loan_repayments (loan_id, repayment_date);

-- 2. Lookup indexes on reversal flags for ledger reconciliation and audit exclusions
CREATE INDEX IF NOT EXISTS idx_investor_txns_reversed 
    ON investor_transactions (is_reversed);

CREATE INDEX IF NOT EXISTS idx_group_cap_alloc_reversed 
    ON group_capital_allocations (is_reversed);

CREATE INDEX IF NOT EXISTS idx_group_withdr_logs_reversed 
    ON group_withdrawal_logs (is_reversed);

CREATE INDEX IF NOT EXISTS idx_central_off_exp_reversed 
    ON central_office_expenses (is_reversed);

CREATE INDEX IF NOT EXISTS idx_investor_pers_exp_reversed 
    ON investor_personal_expenses (is_reversed);

CREATE INDEX IF NOT EXISTS idx_direct_loans_reversed 
    ON direct_individual_loans (is_reversed);

CREATE INDEX IF NOT EXISTS idx_direct_loan_repay_reversed 
    ON direct_loan_repayments (is_reversed);

CREATE INDEX IF NOT EXISTS idx_chit_interbank_reversed 
    ON chit_interbank_transfers (is_reversed);

-- 3. Lookup indexes on backdated flags for chronological audit & recalculation engines
CREATE INDEX IF NOT EXISTS idx_investor_txns_backdated 
    ON investor_transactions (is_backdated);

CREATE INDEX IF NOT EXISTS idx_group_cap_alloc_backdated 
    ON group_capital_allocations (is_backdated);

CREATE INDEX IF NOT EXISTS idx_group_withdr_logs_backdated 
    ON group_withdrawal_logs (is_backdated);

CREATE INDEX IF NOT EXISTS idx_central_off_exp_backdated 
    ON central_office_expenses (is_backdated);

-- 4. Foreign key lookup and status filtering indexes
CREATE INDEX IF NOT EXISTS idx_investors_code 
    ON investors (investor_code);

CREATE INDEX IF NOT EXISTS idx_investors_phone 
    ON investors (phone_number);

CREATE INDEX IF NOT EXISTS idx_investors_chit_member 
    ON investors (linked_chit_member_id);

CREATE INDEX IF NOT EXISTS idx_investors_active 
    ON investors (is_active);

CREATE INDEX IF NOT EXISTS idx_village_groups_code 
    ON village_groups (group_code);

CREATE INDEX IF NOT EXISTS idx_village_groups_status 
    ON village_groups (status);

CREATE INDEX IF NOT EXISTS idx_investor_shares_group 
    ON investor_group_shares (group_id);

CREATE INDEX IF NOT EXISTS idx_investor_shares_investor 
    ON investor_group_shares (investor_id);

CREATE INDEX IF NOT EXISTS idx_group_cap_alloc_investor 
    ON group_capital_allocations (investor_id);

CREATE INDEX IF NOT EXISTS idx_group_withdr_alloc_withdr 
    ON group_withdrawal_allocations (withdrawal_id);

CREATE INDEX IF NOT EXISTS idx_group_withdr_alloc_investor 
    ON group_withdrawal_allocations (investor_id);

CREATE INDEX IF NOT EXISTS idx_central_off_exp_date 
    ON central_office_expenses (expense_date);

CREATE INDEX IF NOT EXISTS idx_central_off_exp_settled 
    ON central_office_expenses (is_settled);

CREATE INDEX IF NOT EXISTS idx_group_exp_alloc_settlement 
    ON group_expense_allocations (settlement_id);

CREATE INDEX IF NOT EXISTS idx_group_exp_alloc_group 
    ON group_expense_allocations (group_id);

CREATE INDEX IF NOT EXISTS idx_direct_loans_status 
    ON direct_individual_loans (status);

CREATE INDEX IF NOT EXISTS idx_direct_loans_investor 
    ON direct_individual_loans (funding_investor_id);

CREATE INDEX IF NOT EXISTS idx_chit_interbank_date 
    ON chit_interbank_transfers (transfer_date);

CREATE INDEX IF NOT EXISTS idx_chit_interbank_group 
    ON chit_interbank_transfers (chit_group_id);
