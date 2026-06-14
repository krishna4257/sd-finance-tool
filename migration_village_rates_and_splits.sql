-- Migration script to add village rates and customer breakdown columns

-- 1. Add columns to village table
ALTER TABLE village ADD COLUMN IF NOT EXISTS interest_rate NUMERIC DEFAULT 0.0;
ALTER TABLE village ADD COLUMN IF NOT EXISTS cutting_rate NUMERIC DEFAULT 0.0;

-- 2. Add columns to customer table (active accounts)
ALTER TABLE customer ADD COLUMN IF NOT EXISTS base_amount NUMERIC DEFAULT 0.0;
ALTER TABLE customer ADD COLUMN IF NOT EXISTS cutting_amount NUMERIC DEFAULT 0.0;
ALTER TABLE customer ADD COLUMN IF NOT EXISTS interest_amount NUMERIC DEFAULT 0.0;

-- 3. Add columns to closed_cust_account table (closed accounts)
ALTER TABLE closed_cust_account ADD COLUMN IF NOT EXISTS base_amount NUMERIC DEFAULT 0.0;
ALTER TABLE closed_cust_account ADD COLUMN IF NOT EXISTS cutting_amount NUMERIC DEFAULT 0.0;
ALTER TABLE closed_cust_account ADD COLUMN IF NOT EXISTS interest_amount NUMERIC DEFAULT 0.0;

-- 4. Add columns to historic_customer_data table (historic accounts)
ALTER TABLE historic_customer_data ADD COLUMN IF NOT EXISTS base_amount NUMERIC DEFAULT 0.0;
ALTER TABLE historic_customer_data ADD COLUMN IF NOT EXISTS cutting_amount NUMERIC DEFAULT 0.0;
ALTER TABLE historic_customer_data ADD COLUMN IF NOT EXISTS interest_amount NUMERIC DEFAULT 0.0;
