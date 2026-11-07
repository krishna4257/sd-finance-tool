-- ==============================================================================
-- Phase 3: High-Performance Composite Indexes for 3-Tier Customer & Payment Views
-- ==============================================================================
-- Idempotent execution script: Safe to run multiple times in all environments.
-- Optimizes queries against v_all_customers, v_all_payments, and core tables.

-- 1. Payment Table Indexes (Active, Closed, Historic)
CREATE INDEX IF NOT EXISTS idx_payment_cid ON payment (cid);
CREATE INDEX IF NOT EXISTS idx_payment_vid_ano_date ON payment (vid, ano, payment_date);
CREATE INDEX IF NOT EXISTS idx_payment_date ON payment (payment_date);

CREATE INDEX IF NOT EXISTS idx_closed_payment_cid ON closed_cust_payment (cid);
CREATE INDEX IF NOT EXISTS idx_closed_payment_vid_ano_date ON closed_cust_payment (vid, ano, payment_date);

CREATE INDEX IF NOT EXISTS idx_historic_payment_cid ON historic_payment_data (cid);
CREATE INDEX IF NOT EXISTS idx_historic_payment_vid_ano_date ON historic_payment_data (vid, ano, payment_date);

-- 2. Customer Table Indexes (Active, Closed, Historic)
CREATE INDEX IF NOT EXISTS idx_customer_vid_ano ON customer (vid, ano);
CREATE INDEX IF NOT EXISTS idx_customer_vid_status ON customer (vid, status);
CREATE INDEX IF NOT EXISTS idx_customer_start_date ON customer (start_date);

CREATE INDEX IF NOT EXISTS idx_closed_customer_vid_ano ON closed_cust_account (vid, ano);
CREATE INDEX IF NOT EXISTS idx_historic_customer_vid_ano ON historic_customer_data (vid, ano);

-- 3. Customer Loan Linkage (v_all_customers / v_all_payments JOIN targets)
CREATE INDEX IF NOT EXISTS idx_loan_link_cid_tier ON customer_loan_link (cid, record_tier);
CREATE INDEX IF NOT EXISTS idx_loan_link_ucid ON customer_loan_link (ucid);

-- 4. Audit Log Indexes
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action_entity ON audit_log (action, entity_type);
