BEGIN;

-- Ensure historic_customer_data table exists
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

-- Ensure historic_payment_data table has cid column
ALTER TABLE historic_payment_data ADD COLUMN IF NOT EXISTS cid bigint;


-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 1
DO $$
DECLARE
    new_cid bigint := 5257587;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 1, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 1;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 1;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 1;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 2
DO $$
DECLARE
    new_cid bigint := 5257588;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 2, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 2;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 2;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 2;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 3
DO $$
DECLARE
    new_cid bigint := 5257589;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 3, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 3;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 3;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 3;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 4
DO $$
DECLARE
    new_cid bigint := 5257590;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 4, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 4;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 4;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 4;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 5
DO $$
DECLARE
    new_cid bigint := 5257591;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 5, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 5;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 5;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 5;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 6
DO $$
DECLARE
    new_cid bigint := 5257592;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 6, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 6;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 6;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 6;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 7
DO $$
DECLARE
    new_cid bigint := 5257593;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 7, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 7;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 7;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 7;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 8
DO $$
DECLARE
    new_cid bigint := 5257594;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 8, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 8;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 8;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 8;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 9
DO $$
DECLARE
    new_cid bigint := 5257595;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 9, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 9;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 9;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 9;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 10
DO $$
DECLARE
    new_cid bigint := 5257596;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 10, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 10;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 10;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 10;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 11
DO $$
DECLARE
    new_cid bigint := 5257597;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 11, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 11;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 11;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 11;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 12
DO $$
DECLARE
    new_cid bigint := 5257598;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 12, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 12;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 12;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 12;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 13
DO $$
DECLARE
    new_cid bigint := 5257599;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 13, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 13;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 13;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 13;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 14
DO $$
DECLARE
    new_cid bigint := 5257600;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 14, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 14;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 14;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 14;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 15
DO $$
DECLARE
    new_cid bigint := 5257601;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 15, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 15;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 15;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 15;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 16
DO $$
DECLARE
    new_cid bigint := 5257602;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 16, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 16;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 16;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 16;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 17
DO $$
DECLARE
    new_cid bigint := 5257603;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 17, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 17;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 17;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 17;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 18
DO $$
DECLARE
    new_cid bigint := 5257604;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 18, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 18;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 18;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 18;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 19
DO $$
DECLARE
    new_cid bigint := 5257605;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 19, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 19;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 19;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 19;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 20
DO $$
DECLARE
    new_cid bigint := 5257606;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 20, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 20;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 20;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 20;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 21
DO $$
DECLARE
    new_cid bigint := 5257607;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 21, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 21;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 21;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 21;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 22
DO $$
DECLARE
    new_cid bigint := 5257608;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 22, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 22;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 22;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 22;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 23
DO $$
DECLARE
    new_cid bigint := 5257609;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 23, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 23;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 23;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 23;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 24
DO $$
DECLARE
    new_cid bigint := 5257610;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 24, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 24;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 24;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 24;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 25
DO $$
DECLARE
    new_cid bigint := 5257611;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 25, 'RTC', 130019, 18, '2014-11-11', '2015-05-05',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 25;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 25;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 25;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 26
DO $$
DECLARE
    new_cid bigint := 5257612;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 26, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 26;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 26;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 26;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 27
DO $$
DECLARE
    new_cid bigint := 5257613;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 27, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 27;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 27;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 27;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 28
DO $$
DECLARE
    new_cid bigint := 5257614;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 28, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        8000.00, 8000.00, 0.0, 320.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 28;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 28;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 28;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 29
DO $$
DECLARE
    new_cid bigint := 5257615;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 29, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 29;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 29;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 29;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 30
DO $$
DECLARE
    new_cid bigint := 5257616;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 30, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 30;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 30;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 30;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 31
DO $$
DECLARE
    new_cid bigint := 5257617;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 31, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 31;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 31;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 31;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 32
DO $$
DECLARE
    new_cid bigint := 5257618;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 32, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 32;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 32;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 32;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 33
DO $$
DECLARE
    new_cid bigint := 5257619;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 33, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 33;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 33;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 33;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 34
DO $$
DECLARE
    new_cid bigint := 5257620;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 34, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 34;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 34;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 34;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 35
DO $$
DECLARE
    new_cid bigint := 5257621;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 35, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 35;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 35;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 35;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 36
DO $$
DECLARE
    new_cid bigint := 5257622;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 36, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 36;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 36;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 36;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 37
DO $$
DECLARE
    new_cid bigint := 5257623;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 37, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 37;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 37;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 37;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 38
DO $$
DECLARE
    new_cid bigint := 5257624;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 38, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 38;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 38;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 38;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 39
DO $$
DECLARE
    new_cid bigint := 5257625;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 39, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 39;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 39;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 39;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 40
DO $$
DECLARE
    new_cid bigint := 5257626;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 40, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 40;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 40;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 40;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 41
DO $$
DECLARE
    new_cid bigint := 5257627;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 41, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 41;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 41;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 41;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 42
DO $$
DECLARE
    new_cid bigint := 5257628;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 42, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 42;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 42;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 42;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 43
DO $$
DECLARE
    new_cid bigint := 5257629;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 43, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 43;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 43;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 43;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 44
DO $$
DECLARE
    new_cid bigint := 5257630;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 44, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 44;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 44;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 44;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 45
DO $$
DECLARE
    new_cid bigint := 5257631;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 45, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 45;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 45;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 45;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 46
DO $$
DECLARE
    new_cid bigint := 5257632;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 46, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 46;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 46;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 46;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 47
DO $$
DECLARE
    new_cid bigint := 5257633;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 47, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 47;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 47;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 47;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 48
DO $$
DECLARE
    new_cid bigint := 5257634;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 48, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 48;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 48;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 48;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 49
DO $$
DECLARE
    new_cid bigint := 5257635;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 49, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 49;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 49;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 49;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 50
DO $$
DECLARE
    new_cid bigint := 5257636;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 50, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 50;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 50;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 50;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 51
DO $$
DECLARE
    new_cid bigint := 5257637;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 51, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 51;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 51;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 51;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 52
DO $$
DECLARE
    new_cid bigint := 5257638;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 52, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 52;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 52;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 52;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 53
DO $$
DECLARE
    new_cid bigint := 5257639;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 53, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 53;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 53;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 53;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 54
DO $$
DECLARE
    new_cid bigint := 5257640;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 54, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 54;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 54;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 54;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 55
DO $$
DECLARE
    new_cid bigint := 5257641;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 55, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 55;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 55;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 55;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 56
DO $$
DECLARE
    new_cid bigint := 5257642;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 56, 'RTC', 130019, 18, '2014-11-18', '2015-05-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 56;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 56;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 56;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 57
DO $$
DECLARE
    new_cid bigint := 5257643;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 57, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 57;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 57;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 57;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 58
DO $$
DECLARE
    new_cid bigint := 5257644;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 58, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 58;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 58;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 58;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 59
DO $$
DECLARE
    new_cid bigint := 5257645;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 59, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 59;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 59;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 59;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 60
DO $$
DECLARE
    new_cid bigint := 5257646;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 60, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 60;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 60;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 60;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 61
DO $$
DECLARE
    new_cid bigint := 5257647;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 61, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 61;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 61;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 61;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 62
DO $$
DECLARE
    new_cid bigint := 5257648;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 62, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 62;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 62;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 62;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 63
DO $$
DECLARE
    new_cid bigint := 5257649;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 63, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 63;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 63;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 63;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 64
DO $$
DECLARE
    new_cid bigint := 5257650;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 64, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 64;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 64;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 64;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 65
DO $$
DECLARE
    new_cid bigint := 5257651;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 65, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 65;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 65;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 65;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 66
DO $$
DECLARE
    new_cid bigint := 5257652;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 66, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 66;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 66;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 66;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 67
DO $$
DECLARE
    new_cid bigint := 5257653;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 67, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 67;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 67;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 67;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 68
DO $$
DECLARE
    new_cid bigint := 5257654;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 68, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 68;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 68;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 68;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 69
DO $$
DECLARE
    new_cid bigint := 5257655;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 69, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 69;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 69;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 69;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 70
DO $$
DECLARE
    new_cid bigint := 5257656;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 70, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 70;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 70;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 70;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 71
DO $$
DECLARE
    new_cid bigint := 5257657;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 71, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 71;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 71;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 71;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 72
DO $$
DECLARE
    new_cid bigint := 5257658;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 72, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 72;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 72;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 72;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 73
DO $$
DECLARE
    new_cid bigint := 5257659;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 73, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 73;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 73;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 73;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 74
DO $$
DECLARE
    new_cid bigint := 5257660;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 74, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 74;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 74;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 74;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 75
DO $$
DECLARE
    new_cid bigint := 5257661;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 75, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 75;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 75;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 75;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 76
DO $$
DECLARE
    new_cid bigint := 5257662;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 76, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 76;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 76;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 76;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 77
DO $$
DECLARE
    new_cid bigint := 5257663;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 77, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 77;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 77;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 77;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 78
DO $$
DECLARE
    new_cid bigint := 5257664;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 78, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 78;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 78;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 78;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 79
DO $$
DECLARE
    new_cid bigint := 5257665;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 79, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 79;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 79;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 79;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 80
DO $$
DECLARE
    new_cid bigint := 5257666;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 80, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 80;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 80;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 80;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 81
DO $$
DECLARE
    new_cid bigint := 5257667;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 81, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 81;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 81;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 81;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 82
DO $$
DECLARE
    new_cid bigint := 5257668;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 82, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 82;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 82;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 82;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 83
DO $$
DECLARE
    new_cid bigint := 5257669;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 83, 'RTC', 130019, 18, '2014-11-25', '2015-05-19',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 83;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 83;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 83;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 84
DO $$
DECLARE
    new_cid bigint := 5257670;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 84, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 84;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 84;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 84;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 85
DO $$
DECLARE
    new_cid bigint := 5257671;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 85, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 85;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 85;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 85;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 86
DO $$
DECLARE
    new_cid bigint := 5257672;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 86, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 86;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 86;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 86;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 87
DO $$
DECLARE
    new_cid bigint := 5257673;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 87, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 87;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 87;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 87;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 88
DO $$
DECLARE
    new_cid bigint := 5257674;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 88, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 88;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 88;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 88;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 89
DO $$
DECLARE
    new_cid bigint := 5257675;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 89, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12800.00, 12800.00, 0.0, 512.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 89;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 89;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 89;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 90
DO $$
DECLARE
    new_cid bigint := 5257676;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 90, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 90;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 90;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 90;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 91
DO $$
DECLARE
    new_cid bigint := 5257677;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 91, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 91;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 91;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 91;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 92
DO $$
DECLARE
    new_cid bigint := 5257678;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 92, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 92;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 92;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 92;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 93
DO $$
DECLARE
    new_cid bigint := 5257679;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 93, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 93;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 93;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 93;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 94
DO $$
DECLARE
    new_cid bigint := 5257680;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 94, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 94;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 94;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 94;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 95
DO $$
DECLARE
    new_cid bigint := 5257681;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 95, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        6250.00, 6250.00, 0.0, 250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 95;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 95;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 95;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 96
DO $$
DECLARE
    new_cid bigint := 5257682;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 96, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12000.00, 12000.00, 0.0, 480.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 96;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 96;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 96;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 97
DO $$
DECLARE
    new_cid bigint := 5257683;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 97, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        5100.00, 5100.00, 0.0, 204.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 97;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 97;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 97;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 98
DO $$
DECLARE
    new_cid bigint := 5257684;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 98, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        6250.00, 6250.00, 0.0, 250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 98;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 98;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 98;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 99
DO $$
DECLARE
    new_cid bigint := 5257685;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 99, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 99;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 99;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 99;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 100
DO $$
DECLARE
    new_cid bigint := 5257686;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 100, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 100;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 100;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 100;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 101
DO $$
DECLARE
    new_cid bigint := 5257687;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 101, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 101;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 101;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 101;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 102
DO $$
DECLARE
    new_cid bigint := 5257688;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 102, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 102;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 102;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 102;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 103
DO $$
DECLARE
    new_cid bigint := 5257689;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 103, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 103;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 103;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 103;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 104
DO $$
DECLARE
    new_cid bigint := 5257690;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 104, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 104;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 104;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 104;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 105
DO $$
DECLARE
    new_cid bigint := 5257691;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 105, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 105;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 105;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 105;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 106
DO $$
DECLARE
    new_cid bigint := 5257692;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 106, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 106;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 106;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 106;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 107
DO $$
DECLARE
    new_cid bigint := 5257693;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 107, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 107;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 107;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 107;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 108
DO $$
DECLARE
    new_cid bigint := 5257694;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 108, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 108;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 108;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 108;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 109
DO $$
DECLARE
    new_cid bigint := 5257695;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 109, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 109;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 109;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 109;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 110
DO $$
DECLARE
    new_cid bigint := 5257696;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 110, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 110;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 110;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 110;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 111
DO $$
DECLARE
    new_cid bigint := 5257697;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 111, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 111;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 111;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 111;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 112
DO $$
DECLARE
    new_cid bigint := 5257698;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 112, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 112;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 112;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 112;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 113
DO $$
DECLARE
    new_cid bigint := 5257699;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 113, 'RTC', 130019, 18, '2014-12-02', '2015-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 113;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 113;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 113;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 114
DO $$
DECLARE
    new_cid bigint := 5257700;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 114, 'RTC', 130019, 18, '2014-12-09', '2015-06-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 114;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 114;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 114;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 115
DO $$
DECLARE
    new_cid bigint := 5257701;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 115, 'RTC', 130019, 18, '2014-12-09', '2015-06-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 115;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 115;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 115;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 116
DO $$
DECLARE
    new_cid bigint := 5257702;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 116, 'RTC', 130019, 18, '2014-12-09', '2015-06-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 116;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 116;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 116;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 117
DO $$
DECLARE
    new_cid bigint := 5257703;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 117, 'RTC', 130019, 18, '2014-12-09', '2015-06-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 117;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 117;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 117;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 118
DO $$
DECLARE
    new_cid bigint := 5257704;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 118, 'RTC', 130019, 18, '2014-12-09', '2015-06-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 118;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 118;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 118;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 119
DO $$
DECLARE
    new_cid bigint := 5257705;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 119, 'RTC', 130019, 18, '2014-12-16', '2015-06-09',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 119;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 119;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 119;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 120
DO $$
DECLARE
    new_cid bigint := 5257706;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 120, 'RTC', 130019, 18, '2014-12-16', '2015-06-09',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 120;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 120;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 120;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 121
DO $$
DECLARE
    new_cid bigint := 5257707;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 121, 'RTC', 130019, 18, '2014-12-16', '2015-06-09',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 121;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 121;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 121;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 122
DO $$
DECLARE
    new_cid bigint := 5257708;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 122, 'RTC', 130019, 18, '2014-12-16', '2015-06-09',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 122;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 122;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 122;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 123
DO $$
DECLARE
    new_cid bigint := 5257709;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 123, 'RTC', 130019, 18, '2014-12-16', '2015-06-09',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 123;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 123;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 123;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 124
DO $$
DECLARE
    new_cid bigint := 5257710;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 124, 'RTC', 130019, 18, '2014-12-16', '2015-06-09',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 124;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 124;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 124;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 125
DO $$
DECLARE
    new_cid bigint := 5257711;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 125, 'RTC', 130019, 18, '2014-12-16', '2015-06-09',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 125;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 125;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 125;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 126
DO $$
DECLARE
    new_cid bigint := 5257712;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 126, 'RTC', 130019, 18, '2014-12-16', '2015-06-09',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 126;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 126;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 126;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 127
DO $$
DECLARE
    new_cid bigint := 5257713;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 127, 'RTC', 130019, 18, '2014-12-23', '2015-06-16',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 127;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 127;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 127;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 128
DO $$
DECLARE
    new_cid bigint := 5257714;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 128, 'RTC', 130019, 18, '2014-12-23', '2015-06-16',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 128;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 128;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 128;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 129
DO $$
DECLARE
    new_cid bigint := 5257715;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 129, 'RTC', 130019, 18, '2014-12-23', '2015-06-16',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 129;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 129;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 129;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 130
DO $$
DECLARE
    new_cid bigint := 5257716;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 130, 'RTC', 130019, 18, '2014-12-23', '2015-06-16',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 130;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 130;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 130;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 131
DO $$
DECLARE
    new_cid bigint := 5257717;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 131, 'RTC', 130019, 18, '2014-12-23', '2015-06-16',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 131;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 131;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 131;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 132
DO $$
DECLARE
    new_cid bigint := 5257718;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 132, 'RTC', 130019, 18, '2014-12-23', '2015-06-16',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 132;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 132;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 132;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 133
DO $$
DECLARE
    new_cid bigint := 5257719;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 133, 'RTC', 130019, 18, '2014-12-30', '2015-06-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 133;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 133;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 133;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 134
DO $$
DECLARE
    new_cid bigint := 5257720;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 134, 'RTC', 130019, 18, '2014-12-30', '2015-06-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 134;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 134;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 134;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 135
DO $$
DECLARE
    new_cid bigint := 5257721;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 135, 'RTC', 130019, 18, '2014-12-30', '2015-06-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 135;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 135;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 135;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 136
DO $$
DECLARE
    new_cid bigint := 5257722;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 136, 'RTC', 130019, 18, '2014-12-30', '2015-06-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 136;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 136;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 136;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 137
DO $$
DECLARE
    new_cid bigint := 5257723;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 137, 'RTC', 130019, 18, '2014-12-30', '2015-06-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 137;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 137;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 137;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 138
DO $$
DECLARE
    new_cid bigint := 5257724;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 138, 'RTC', 130019, 18, '2014-12-30', '2015-06-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 138;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 138;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 138;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 139
DO $$
DECLARE
    new_cid bigint := 5257725;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 139, 'RTC', 130019, 18, '2014-12-30', '2015-06-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 139;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 139;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 139;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 140
DO $$
DECLARE
    new_cid bigint := 5257726;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 140, 'RTC', 130019, 18, '2014-12-30', '2015-06-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 140;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 140;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 140;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 141
DO $$
DECLARE
    new_cid bigint := 5257727;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 141, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 141;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 141;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 141;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 142
DO $$
DECLARE
    new_cid bigint := 5257728;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 142, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 142;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 142;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 142;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 143
DO $$
DECLARE
    new_cid bigint := 5257729;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 143, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 143;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 143;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 143;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 144
DO $$
DECLARE
    new_cid bigint := 5257730;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 144, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 144;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 144;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 144;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 145
DO $$
DECLARE
    new_cid bigint := 5257731;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 145, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 145;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 145;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 145;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 146
DO $$
DECLARE
    new_cid bigint := 5257732;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 146, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 146;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 146;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 146;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 147
DO $$
DECLARE
    new_cid bigint := 5257733;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 147, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 147;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 147;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 147;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 148
DO $$
DECLARE
    new_cid bigint := 5257734;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 148, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 148;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 148;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 148;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 149
DO $$
DECLARE
    new_cid bigint := 5257735;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 149, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 149;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 149;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 149;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 150
DO $$
DECLARE
    new_cid bigint := 5257736;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 150, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 150;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 150;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 150;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 151
DO $$
DECLARE
    new_cid bigint := 5257737;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 151, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 151;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 151;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 151;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 152
DO $$
DECLARE
    new_cid bigint := 5257738;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 152, 'RTC', 130019, 18, '2015-01-06', '2015-06-30',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-06-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 152;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 152;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 152;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 153
DO $$
DECLARE
    new_cid bigint := 5257739;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 153, 'RTC', 130019, 18, '2015-01-13', '2015-07-07',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 153;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 153;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 153;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 154
DO $$
DECLARE
    new_cid bigint := 5257740;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 154, 'RTC', 130019, 18, '2015-01-13', '2015-07-07',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 154;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 154;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 154;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 155
DO $$
DECLARE
    new_cid bigint := 5257741;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 155, 'RTC', 130019, 18, '2015-01-13', '2015-07-07',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 155;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 155;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 155;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 156
DO $$
DECLARE
    new_cid bigint := 5257742;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 156, 'RTC', 130019, 18, '2015-01-13', '2015-07-07',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 156;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 156;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 156;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 157
DO $$
DECLARE
    new_cid bigint := 5257743;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 157, 'RTC', 130019, 18, '2015-01-13', '2015-07-07',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 157;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 157;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 157;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 158
DO $$
DECLARE
    new_cid bigint := 5257744;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 158, 'RTC', 130019, 18, '2015-01-13', '2015-07-07',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 158;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 158;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 158;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 161
DO $$
DECLARE
    new_cid bigint := 5257745;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 161, 'RTC', 130019, 18, '2015-01-13', '2015-07-07',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 161;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 161;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 161;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 162
DO $$
DECLARE
    new_cid bigint := 5257746;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 162, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 162;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 162;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 162;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 163
DO $$
DECLARE
    new_cid bigint := 5257747;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 163, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 163;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 163;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 163;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 164
DO $$
DECLARE
    new_cid bigint := 5257748;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 164, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 164;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 164;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 164;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 166
DO $$
DECLARE
    new_cid bigint := 5257749;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 166, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 166;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 166;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 166;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 167
DO $$
DECLARE
    new_cid bigint := 5257750;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 167, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 167;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 167;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 167;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 169
DO $$
DECLARE
    new_cid bigint := 5257751;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 169, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 169;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 169;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 169;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 170
DO $$
DECLARE
    new_cid bigint := 5257752;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 170, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        6250.00, 6250.00, 0.0, 250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 170;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 170;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 170;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 171
DO $$
DECLARE
    new_cid bigint := 5257753;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 171, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 171;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 171;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 171;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 172
DO $$
DECLARE
    new_cid bigint := 5257754;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 172, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 172;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 172;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 172;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 173
DO $$
DECLARE
    new_cid bigint := 5257755;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 173, 'RTC', 130019, 18, '2015-01-20', '2015-07-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 173;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 173;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 173;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 174
DO $$
DECLARE
    new_cid bigint := 5257756;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 174, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 174;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 174;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 174;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 175
DO $$
DECLARE
    new_cid bigint := 5257757;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 175, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 175;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 175;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 175;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 176
DO $$
DECLARE
    new_cid bigint := 5257758;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 176, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 176;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 176;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 176;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 177
DO $$
DECLARE
    new_cid bigint := 5257759;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 177, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 177;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 177;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 177;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 178
DO $$
DECLARE
    new_cid bigint := 5257760;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 178, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        11250.00, 11250.00, 0.0, 450.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 178;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 178;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 178;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 179
DO $$
DECLARE
    new_cid bigint := 5257761;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 179, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 179;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 179;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 179;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 180
DO $$
DECLARE
    new_cid bigint := 5257762;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 180, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 180;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 180;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 180;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 181
DO $$
DECLARE
    new_cid bigint := 5257763;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 181, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 181;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 181;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 181;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 182
DO $$
DECLARE
    new_cid bigint := 5257764;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 182, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 182;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 182;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 182;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 183
DO $$
DECLARE
    new_cid bigint := 5257765;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 183, 'RTC', 130019, 18, '2015-01-27', '2015-07-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-07-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 183;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 183;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 183;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 185
DO $$
DECLARE
    new_cid bigint := 5257766;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 185, 'RTC', 130019, 18, '2015-02-10', '2015-08-04',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-08-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 185;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 185;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 185;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 186
DO $$
DECLARE
    new_cid bigint := 5257767;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 186, 'RTC', 130019, 18, '2015-02-10', '2015-08-04',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-08-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 186;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 186;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 186;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 187
DO $$
DECLARE
    new_cid bigint := 5257768;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 187, 'RTC', 130019, 18, '2015-02-10', '2015-08-04',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-08-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 187;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 187;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 187;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 188
DO $$
DECLARE
    new_cid bigint := 5257769;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 188, 'RTC', 130019, 18, '2015-02-17', '2015-08-11',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-08-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 188;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 188;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 188;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 189
DO $$
DECLARE
    new_cid bigint := 5257770;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 189, 'RTC', 130019, 18, '2015-03-17', '2015-09-08',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-08', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 189;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 189;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 189;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 190
DO $$
DECLARE
    new_cid bigint := 5257771;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 190, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 190;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 190;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 190;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 191
DO $$
DECLARE
    new_cid bigint := 5257772;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 191, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 191;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 191;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 191;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 192
DO $$
DECLARE
    new_cid bigint := 5257773;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 192, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 192;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 192;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 192;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 193
DO $$
DECLARE
    new_cid bigint := 5257774;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 193, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 193;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 193;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 193;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 195
DO $$
DECLARE
    new_cid bigint := 5257775;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 195, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 195;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 195;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 195;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 196
DO $$
DECLARE
    new_cid bigint := 5257776;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 196, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15500.00, 15500.00, 0.0, 620.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 196;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 196;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 196;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 197
DO $$
DECLARE
    new_cid bigint := 5257777;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 197, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 197;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 197;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 197;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 198
DO $$
DECLARE
    new_cid bigint := 5257778;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 198, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 198;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 198;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 198;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 199
DO $$
DECLARE
    new_cid bigint := 5257779;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 199, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 199;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 199;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 199;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 200
DO $$
DECLARE
    new_cid bigint := 5257780;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 200, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 200;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 200;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 200;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 201
DO $$
DECLARE
    new_cid bigint := 5257781;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 201, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 201;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 201;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 201;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 202
DO $$
DECLARE
    new_cid bigint := 5257782;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 202, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        14500.00, 14500.00, 0.0, 580.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 202;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 202;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 202;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 203
DO $$
DECLARE
    new_cid bigint := 5257783;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 203, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 203;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 203;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 203;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 204
DO $$
DECLARE
    new_cid bigint := 5257784;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 204, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 204;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 204;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 204;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 206
DO $$
DECLARE
    new_cid bigint := 5257785;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 206, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 206;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 206;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 206;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 208
DO $$
DECLARE
    new_cid bigint := 5257786;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 208, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 208;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 208;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 208;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 209
DO $$
DECLARE
    new_cid bigint := 5257787;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 209, 'RTC', 130019, 18, '2015-03-29', '2015-09-20',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 209;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 209;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 209;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 210
DO $$
DECLARE
    new_cid bigint := 5257788;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 210, 'RTC', 130019, 18, '2015-05-05', '2015-10-27',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-10-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 210;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 210;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 210;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 211
DO $$
DECLARE
    new_cid bigint := 5257789;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 211, 'RTC', 130019, 18, '2015-05-05', '2015-10-27',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-10-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 211;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 211;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 211;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 212
DO $$
DECLARE
    new_cid bigint := 5257790;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 212, 'RTC', 130019, 18, '2015-05-05', '2015-10-27',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-10-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 212;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 212;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 212;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 217
DO $$
DECLARE
    new_cid bigint := 5257791;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 217, 'RTC', 130019, 18, '2015-05-05', '2015-10-27',
        16875.00, 16875.00, 0.0, 675.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-10-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 217;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 217;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 217;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 218
DO $$
DECLARE
    new_cid bigint := 5257792;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 218, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 218;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 218;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 218;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 219
DO $$
DECLARE
    new_cid bigint := 5257793;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 219, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 219;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 219;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 219;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 220
DO $$
DECLARE
    new_cid bigint := 5257794;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 220, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 220;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 220;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 220;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 221
DO $$
DECLARE
    new_cid bigint := 5257795;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 221, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 221;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 221;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 221;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 222
DO $$
DECLARE
    new_cid bigint := 5257796;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 222, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 222;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 222;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 222;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 223
DO $$
DECLARE
    new_cid bigint := 5257797;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 223, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 223;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 223;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 223;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 226
DO $$
DECLARE
    new_cid bigint := 5257798;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 226, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 226;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 226;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 226;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 227
DO $$
DECLARE
    new_cid bigint := 5257799;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 227, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 227;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 227;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 227;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 230
DO $$
DECLARE
    new_cid bigint := 5257800;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 230, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 230;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 230;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 230;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 231
DO $$
DECLARE
    new_cid bigint := 5257801;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 231, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 231;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 231;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 231;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 232
DO $$
DECLARE
    new_cid bigint := 5257802;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 232, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 232;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 232;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 232;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 234
DO $$
DECLARE
    new_cid bigint := 5257803;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 234, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 234;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 234;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 234;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 235
DO $$
DECLARE
    new_cid bigint := 5257804;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 235, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 235;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 235;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 235;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 236
DO $$
DECLARE
    new_cid bigint := 5257805;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 236, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 236;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 236;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 236;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 237
DO $$
DECLARE
    new_cid bigint := 5257806;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 237, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 237;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 237;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 237;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 238
DO $$
DECLARE
    new_cid bigint := 5257807;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 238, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 238;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 238;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 238;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 239
DO $$
DECLARE
    new_cid bigint := 5257808;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 239, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 239;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 239;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 239;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 240
DO $$
DECLARE
    new_cid bigint := 5257809;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 240, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 240;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 240;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 240;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 241
DO $$
DECLARE
    new_cid bigint := 5257810;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 241, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 241;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 241;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 241;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 244
DO $$
DECLARE
    new_cid bigint := 5257811;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 244, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 244;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 244;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 244;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 245
DO $$
DECLARE
    new_cid bigint := 5257812;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 245, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 245;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 245;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 245;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 246
DO $$
DECLARE
    new_cid bigint := 5257813;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 246, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 246;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 246;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 246;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 247
DO $$
DECLARE
    new_cid bigint := 5257814;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 247, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 247;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 247;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 247;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 248
DO $$
DECLARE
    new_cid bigint := 5257815;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 248, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 248;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 248;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 248;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 249
DO $$
DECLARE
    new_cid bigint := 5257816;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 249, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 249;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 249;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 249;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 250
DO $$
DECLARE
    new_cid bigint := 5257817;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 250, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 250;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 250;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 250;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 251
DO $$
DECLARE
    new_cid bigint := 5257818;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 251, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 251;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 251;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 251;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 252
DO $$
DECLARE
    new_cid bigint := 5257819;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 252, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 252;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 252;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 252;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 253
DO $$
DECLARE
    new_cid bigint := 5257820;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 253, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 253;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 253;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 253;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 254
DO $$
DECLARE
    new_cid bigint := 5257821;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 254, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 254;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 254;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 254;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 255
DO $$
DECLARE
    new_cid bigint := 5257822;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 255, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 255;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 255;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 255;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 256
DO $$
DECLARE
    new_cid bigint := 5257823;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 256, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 256;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 256;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 256;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 258
DO $$
DECLARE
    new_cid bigint := 5257824;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 258, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 258;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 258;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 258;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 259
DO $$
DECLARE
    new_cid bigint := 5257825;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 259, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 259;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 259;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 259;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 260
DO $$
DECLARE
    new_cid bigint := 5257826;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 260, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 260;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 260;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 260;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 261
DO $$
DECLARE
    new_cid bigint := 5257827;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 261, 'RTC', 130019, 18, '2015-05-26', '2015-11-17',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 261;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 261;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 261;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 262
DO $$
DECLARE
    new_cid bigint := 5257828;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 262, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 262;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 262;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 262;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 263
DO $$
DECLARE
    new_cid bigint := 5257829;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 263, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 263;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 263;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 263;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 266
DO $$
DECLARE
    new_cid bigint := 5257830;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 266, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 266;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 266;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 266;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 267
DO $$
DECLARE
    new_cid bigint := 5257831;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 267, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 267;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 267;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 267;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 268
DO $$
DECLARE
    new_cid bigint := 5257832;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 268, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 268;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 268;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 268;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 269
DO $$
DECLARE
    new_cid bigint := 5257833;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 269, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 269;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 269;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 269;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 272
DO $$
DECLARE
    new_cid bigint := 5257834;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 272, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 272;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 272;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 272;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 274
DO $$
DECLARE
    new_cid bigint := 5257835;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 274, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 274;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 274;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 274;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 276
DO $$
DECLARE
    new_cid bigint := 5257836;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 276, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 276;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 276;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 276;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 277
DO $$
DECLARE
    new_cid bigint := 5257837;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 277, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 277;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 277;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 277;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 279
DO $$
DECLARE
    new_cid bigint := 5257838;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 279, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 279;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 279;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 279;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 280
DO $$
DECLARE
    new_cid bigint := 5257839;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 280, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 280;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 280;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 280;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 281
DO $$
DECLARE
    new_cid bigint := 5257840;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 281, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 281;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 281;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 281;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 282
DO $$
DECLARE
    new_cid bigint := 5257841;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 282, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 282;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 282;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 282;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 283
DO $$
DECLARE
    new_cid bigint := 5257842;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 283, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 283;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 283;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 283;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 292
DO $$
DECLARE
    new_cid bigint := 5257843;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 292, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 292;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 292;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 292;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 293
DO $$
DECLARE
    new_cid bigint := 5257844;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 293, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 293;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 293;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 293;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 294
DO $$
DECLARE
    new_cid bigint := 5257845;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 294, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        13500.00, 13500.00, 0.0, 540.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 294;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 294;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 294;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 295
DO $$
DECLARE
    new_cid bigint := 5257846;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 295, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        14400.00, 14400.00, 0.0, 576.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 295;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 295;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 295;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 296
DO $$
DECLARE
    new_cid bigint := 5257847;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 296, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        22500.00, 22500.00, 0.0, 900.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 296;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 296;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 296;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 297
DO $$
DECLARE
    new_cid bigint := 5257848;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 297, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 297;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 297;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 297;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 298
DO $$
DECLARE
    new_cid bigint := 5257849;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 298, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 298;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 298;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 298;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 299
DO $$
DECLARE
    new_cid bigint := 5257850;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 299, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 299;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 299;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 299;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 301
DO $$
DECLARE
    new_cid bigint := 5257851;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 301, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 301;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 301;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 301;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 302
DO $$
DECLARE
    new_cid bigint := 5257852;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 302, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 302;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 302;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 302;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 303
DO $$
DECLARE
    new_cid bigint := 5257853;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 303, 'RTC', 130019, 18, '2015-05-11', '2015-11-02',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2015-11-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 303;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 303;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 303;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 304
DO $$
DECLARE
    new_cid bigint := 5257854;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 304, 'RTC', 130019, 18, '2015-09-15', '2016-03-08',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-03-08', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 304;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 304;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 304;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 307
DO $$
DECLARE
    new_cid bigint := 5257855;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 307, 'RTC', 130019, 18, '2015-09-22', '2016-03-15',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-03-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 307;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 307;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 307;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 308
DO $$
DECLARE
    new_cid bigint := 5257856;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 308, 'RTC', 130019, 18, '2015-09-29', '2016-03-22',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-03-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 308;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 308;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 308;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 309
DO $$
DECLARE
    new_cid bigint := 5257857;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 309, 'RTC', 130019, 18, '2015-09-29', '2016-03-22',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-03-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 309;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 309;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 309;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 310
DO $$
DECLARE
    new_cid bigint := 5257858;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 310, 'RTC', 130019, 18, '2015-10-06', '2016-03-29',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-03-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 310;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 310;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 310;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 311
DO $$
DECLARE
    new_cid bigint := 5257859;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 311, 'RTC', 130019, 18, '2015-10-06', '2016-03-29',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-03-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 311;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 311;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 311;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 312
DO $$
DECLARE
    new_cid bigint := 5257860;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 312, 'RTC', 130019, 18, '2015-10-06', '2016-03-29',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-03-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 312;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 312;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 312;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 313
DO $$
DECLARE
    new_cid bigint := 5257861;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 313, 'RTC', 130019, 18, '2015-10-06', '2016-03-29',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-03-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 313;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 313;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 313;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 314
DO $$
DECLARE
    new_cid bigint := 5257862;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 314, 'RTC', 130019, 18, '2015-10-13', '2016-04-05',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-04-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 314;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 314;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 314;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 315
DO $$
DECLARE
    new_cid bigint := 5257863;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 315, 'RTC', 130019, 18, '2015-10-13', '2016-04-05',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-04-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 315;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 315;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 315;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 316
DO $$
DECLARE
    new_cid bigint := 5257864;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 316, 'RTC', 130019, 18, '2015-10-27', '2016-04-19',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-04-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 316;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 316;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 316;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 317
DO $$
DECLARE
    new_cid bigint := 5257865;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 317, 'RTC', 130019, 18, '2015-10-27', '2016-04-19',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-04-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 317;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 317;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 317;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 318
DO $$
DECLARE
    new_cid bigint := 5257866;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 318, 'RTC', 130019, 18, '2015-10-27', '2016-04-19',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-04-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 318;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 318;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 318;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 320
DO $$
DECLARE
    new_cid bigint := 5257867;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 320, 'RTC', 130019, 18, '2015-11-03', '2016-04-26',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-04-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 320;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 320;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 320;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 321
DO $$
DECLARE
    new_cid bigint := 5257868;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 321, 'RTC', 130019, 18, '2015-11-03', '2016-04-26',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-04-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 321;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 321;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 321;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 322
DO $$
DECLARE
    new_cid bigint := 5257869;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 322, 'RTC', 130019, 18, '2015-11-03', '2016-04-26',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-04-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 322;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 322;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 322;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 323
DO $$
DECLARE
    new_cid bigint := 5257870;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 323, 'RTC', 130019, 18, '2015-11-10', '2016-05-03',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 323;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 323;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 323;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 324
DO $$
DECLARE
    new_cid bigint := 5257871;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 324, 'RTC', 130019, 18, '2015-11-10', '2016-05-03',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 324;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 324;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 324;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 325
DO $$
DECLARE
    new_cid bigint := 5257872;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 325, 'RTC', 130019, 18, '2015-11-10', '2016-05-03',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 325;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 325;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 325;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 326
DO $$
DECLARE
    new_cid bigint := 5257873;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 326, 'RTC', 130019, 18, '2015-11-10', '2016-05-03',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 326;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 326;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 326;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 327
DO $$
DECLARE
    new_cid bigint := 5257874;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 327, 'RTC', 130019, 18, '2015-11-10', '2016-05-03',
        17500.00, 17500.00, 0.0, 700.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 327;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 327;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 327;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 328
DO $$
DECLARE
    new_cid bigint := 5257875;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 328, 'RTC', 130019, 18, '2015-11-10', '2016-05-03',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 328;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 328;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 328;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 329
DO $$
DECLARE
    new_cid bigint := 5257876;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 329, 'RTC', 130019, 18, '2015-11-10', '2016-05-03',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 329;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 329;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 329;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 331
DO $$
DECLARE
    new_cid bigint := 5257877;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 331, 'RTC', 130019, 18, '2015-11-17', '2016-05-10',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 331;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 331;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 331;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 332
DO $$
DECLARE
    new_cid bigint := 5257878;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 332, 'RTC', 130019, 18, '2015-11-17', '2016-05-10',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 332;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 332;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 332;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 333
DO $$
DECLARE
    new_cid bigint := 5257879;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 333, 'RTC', 130019, 18, '2015-11-17', '2016-05-10',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 333;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 333;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 333;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 334
DO $$
DECLARE
    new_cid bigint := 5257880;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 334, 'RTC', 130019, 18, '2015-11-17', '2016-05-10',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 334;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 334;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 334;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 335
DO $$
DECLARE
    new_cid bigint := 5257881;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 335, 'RTC', 130019, 18, '2015-11-17', '2016-05-10',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 335;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 335;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 335;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 336
DO $$
DECLARE
    new_cid bigint := 5257882;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 336, 'RTC', 130019, 18, '2015-11-24', '2016-05-17',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 336;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 336;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 336;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 337
DO $$
DECLARE
    new_cid bigint := 5257883;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 337, 'RTC', 130019, 18, '2015-12-01', '2016-05-24',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-24', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 337;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 337;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 337;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 338
DO $$
DECLARE
    new_cid bigint := 5257884;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 338, 'RTC', 130019, 18, '2015-12-08', '2016-05-31',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 338;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 338;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 338;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 339
DO $$
DECLARE
    new_cid bigint := 5257885;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 339, 'RTC', 130019, 18, '2015-12-08', '2016-05-31',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-05-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 339;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 339;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 339;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 340
DO $$
DECLARE
    new_cid bigint := 5257886;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 340, 'RTC', 130019, 18, '2015-12-15', '2016-06-07',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-06-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 340;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 340;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 340;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 341
DO $$
DECLARE
    new_cid bigint := 5257887;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 341, 'RTC', 130019, 18, '2015-12-15', '2016-06-07',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-06-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 341;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 341;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 341;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 342
DO $$
DECLARE
    new_cid bigint := 5257888;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 342, 'RTC', 130019, 18, '2015-12-22', '2016-06-14',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-06-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 342;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 342;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 342;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 343
DO $$
DECLARE
    new_cid bigint := 5257889;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 343, 'RTC', 130019, 18, '2015-12-29', '2016-06-21',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-06-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 343;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 343;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 343;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 344
DO $$
DECLARE
    new_cid bigint := 5257890;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 344, 'RTC', 130019, 18, '2016-01-26', '2016-07-19',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-07-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 344;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 344;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 344;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 345
DO $$
DECLARE
    new_cid bigint := 5257891;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 345, 'RTC', 130019, 18, '2016-02-02', '2016-07-26',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-07-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 345;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 345;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 345;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 346
DO $$
DECLARE
    new_cid bigint := 5257892;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 346, 'RTC', 130019, 18, '2016-02-09', '2016-08-02',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-08-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 346;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 346;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 346;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 347
DO $$
DECLARE
    new_cid bigint := 5257893;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 347, 'RTC', 130019, 18, '2016-02-16', '2016-08-09',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-08-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 347;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 347;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 347;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 348
DO $$
DECLARE
    new_cid bigint := 5257894;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 348, 'RTC', 130019, 18, '2016-03-22', '2016-09-13',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 348;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 348;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 348;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 349
DO $$
DECLARE
    new_cid bigint := 5257895;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 349, 'RTC', 130019, 18, '2016-03-22', '2016-09-13',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 349;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 349;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 349;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 350
DO $$
DECLARE
    new_cid bigint := 5257896;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 350, 'RTC', 130019, 18, '2016-04-05', '2016-09-27',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 350;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 350;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 350;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 351
DO $$
DECLARE
    new_cid bigint := 5257897;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 351, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 351;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 351;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 351;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 352
DO $$
DECLARE
    new_cid bigint := 5257898;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 352, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 352;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 352;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 352;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 353
DO $$
DECLARE
    new_cid bigint := 5257899;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 353, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 353;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 353;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 353;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 354
DO $$
DECLARE
    new_cid bigint := 5257900;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 354, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 354;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 354;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 354;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 356
DO $$
DECLARE
    new_cid bigint := 5257901;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 356, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 356;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 356;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 356;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 357
DO $$
DECLARE
    new_cid bigint := 5257902;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 357, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 357;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 357;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 357;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 358
DO $$
DECLARE
    new_cid bigint := 5257903;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 358, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 358;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 358;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 358;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 359
DO $$
DECLARE
    new_cid bigint := 5257904;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 359, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 359;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 359;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 359;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 360
DO $$
DECLARE
    new_cid bigint := 5257905;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 360, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 360;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 360;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 360;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 362
DO $$
DECLARE
    new_cid bigint := 5257906;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 362, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 362;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 362;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 362;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 363
DO $$
DECLARE
    new_cid bigint := 5257907;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 363, 'RTC', 130019, 18, '2016-04-03', '2016-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 363;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 363;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 363;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 364
DO $$
DECLARE
    new_cid bigint := 5257908;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 364, 'RTC', 130019, 18, '2016-05-17', '2016-11-08',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-11-08', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 364;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 364;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 364;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 365
DO $$
DECLARE
    new_cid bigint := 5257909;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 365, 'RTC', 130019, 18, '2016-05-17', '2016-11-08',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-11-08', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 365;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 365;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 365;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 367
DO $$
DECLARE
    new_cid bigint := 5257910;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 367, 'RTC', 130019, 18, '2016-05-24', '2016-11-15',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-11-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 367;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 367;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 367;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 368
DO $$
DECLARE
    new_cid bigint := 5257911;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 368, 'RTC', 130019, 18, '2016-05-24', '2016-11-15',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-11-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 368;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 368;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 368;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 369
DO $$
DECLARE
    new_cid bigint := 5257912;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 369, 'RTC', 130019, 18, '2016-05-24', '2016-11-15',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-11-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 369;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 369;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 369;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 370
DO $$
DECLARE
    new_cid bigint := 5257913;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 370, 'RTC', 130019, 18, '2016-06-07', '2016-11-29',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-11-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 370;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 370;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 370;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 371
DO $$
DECLARE
    new_cid bigint := 5257914;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 371, 'RTC', 130019, 18, '2016-06-07', '2016-11-29',
        8750.00, 8750.00, 0.0, 350.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-11-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 371;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 371;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 371;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 372
DO $$
DECLARE
    new_cid bigint := 5257915;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 372, 'RTC', 130019, 18, '2016-06-14', '2016-12-06',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-12-06', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 372;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 372;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 372;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 373
DO $$
DECLARE
    new_cid bigint := 5257916;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 373, 'RTC', 130019, 18, '2016-07-05', '2016-12-27',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-12-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 373;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 373;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 373;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 374
DO $$
DECLARE
    new_cid bigint := 5257917;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 374, 'RTC', 130019, 18, '2016-07-05', '2016-12-27',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2016-12-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 374;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 374;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 374;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 375
DO $$
DECLARE
    new_cid bigint := 5257918;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 375, 'RTC', 130019, 18, '2016-07-12', '2017-01-03',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-01-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 375;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 375;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 375;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 376
DO $$
DECLARE
    new_cid bigint := 5257919;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 376, 'RTC', 130019, 18, '2016-07-19', '2017-01-10',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-01-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 376;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 376;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 376;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 377
DO $$
DECLARE
    new_cid bigint := 5257920;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 377, 'RTC', 130019, 18, '2016-08-02', '2017-01-24',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-01-24', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 377;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 377;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 377;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 380
DO $$
DECLARE
    new_cid bigint := 5257921;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 380, 'RTC', 130019, 18, '2016-09-20', '2017-03-14',
        17300.00, 17300.00, 0.0, 692.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-03-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 380;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 380;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 380;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 381
DO $$
DECLARE
    new_cid bigint := 5257922;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 381, 'RTC', 130019, 18, '2016-09-20', '2017-03-14',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-03-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 381;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 381;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 381;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 382
DO $$
DECLARE
    new_cid bigint := 5257923;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 382, 'RTC', 130019, 18, '2016-09-27', '2017-03-21',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-03-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 382;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 382;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 382;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 383
DO $$
DECLARE
    new_cid bigint := 5257924;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 383, 'RTC', 130019, 18, '2016-09-27', '2017-03-21',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-03-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 383;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 383;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 383;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 384
DO $$
DECLARE
    new_cid bigint := 5257925;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 384, 'RTC', 130019, 18, '2016-09-27', '2017-03-21',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-03-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 384;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 384;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 384;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 385
DO $$
DECLARE
    new_cid bigint := 5257926;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 385, 'RTC', 130019, 18, '2016-10-04', '2017-03-28',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-03-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 385;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 385;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 385;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 386
DO $$
DECLARE
    new_cid bigint := 5257927;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 386, 'RTC', 130019, 18, '2016-10-11', '2017-04-04',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-04-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 386;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 386;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 386;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 387
DO $$
DECLARE
    new_cid bigint := 5257928;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 387, 'RTC', 130019, 18, '2016-10-25', '2017-04-18',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-04-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 387;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 387;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 387;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 388
DO $$
DECLARE
    new_cid bigint := 5257929;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 388, 'RTC', 130019, 18, '2016-11-01', '2017-04-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-04-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 388;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 388;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 388;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 389
DO $$
DECLARE
    new_cid bigint := 5257930;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 389, 'RTC', 130019, 18, '2016-11-01', '2017-04-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-04-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 389;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 389;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 389;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 390
DO $$
DECLARE
    new_cid bigint := 5257931;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 390, 'RTC', 130019, 18, '2016-11-08', '2017-05-02',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-05-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 390;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 390;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 390;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 391
DO $$
DECLARE
    new_cid bigint := 5257932;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 391, 'RTC', 130019, 18, '2016-11-15', '2017-05-09',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-05-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 391;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 391;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 391;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 392
DO $$
DECLARE
    new_cid bigint := 5257933;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 392, 'RTC', 130019, 18, '2016-11-22', '2017-05-16',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-05-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 392;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 392;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 392;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 394
DO $$
DECLARE
    new_cid bigint := 5257934;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 394, 'RTC', 130019, 18, '2016-12-06', '2017-05-30',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-05-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 394;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 394;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 394;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 395
DO $$
DECLARE
    new_cid bigint := 5257935;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 395, 'RTC', 130019, 18, '2017-01-17', '2017-07-11',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-07-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 395;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 395;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 395;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 397
DO $$
DECLARE
    new_cid bigint := 5257936;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 397, 'RTC', 130019, 18, '2017-01-24', '2017-07-18',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-07-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 397;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 397;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 397;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 398
DO $$
DECLARE
    new_cid bigint := 5257937;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 398, 'RTC', 130019, 18, '2017-01-24', '2017-07-18',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-07-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 398;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 398;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 398;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 399
DO $$
DECLARE
    new_cid bigint := 5257938;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 399, 'RTC', 130019, 18, '2017-03-14', '2017-09-05',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-09-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 399;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 399;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 399;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 400
DO $$
DECLARE
    new_cid bigint := 5257939;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 400, 'RTC', 130019, 18, '2017-03-14', '2017-09-05',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-09-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 400;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 400;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 400;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 401
DO $$
DECLARE
    new_cid bigint := 5257940;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 401, 'RTC', 130019, 18, '2017-04-04', '2017-09-26',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-09-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 401;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 401;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 401;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 402
DO $$
DECLARE
    new_cid bigint := 5257941;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 402, 'RTC', 130019, 18, '2017-04-11', '2017-10-03',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-10-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 402;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 402;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 402;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 403
DO $$
DECLARE
    new_cid bigint := 5257942;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 403, 'RTC', 130019, 18, '2017-04-11', '2017-10-03',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-10-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 403;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 403;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 403;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 404
DO $$
DECLARE
    new_cid bigint := 5257943;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 404, 'RTC', 130019, 18, '2017-04-11', '2017-10-03',
        21250.00, 21250.00, 0.0, 850.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-10-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 404;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 404;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 404;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 405
DO $$
DECLARE
    new_cid bigint := 5257944;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 405, 'RTC', 130019, 18, '2017-04-11', '2017-10-03',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-10-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 405;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 405;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 405;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 406
DO $$
DECLARE
    new_cid bigint := 5257945;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 406, 'RTC', 130019, 18, '2017-04-18', '2017-10-10',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-10-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 406;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 406;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 406;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 407
DO $$
DECLARE
    new_cid bigint := 5257946;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 407, 'RTC', 130019, 18, '2017-04-25', '2017-10-17',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-10-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 407;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 407;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 407;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 408
DO $$
DECLARE
    new_cid bigint := 5257947;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 408, 'RTC', 130019, 18, '2017-04-25', '2017-10-17',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-10-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 408;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 408;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 408;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 409
DO $$
DECLARE
    new_cid bigint := 5257948;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 409, 'RTC', 130019, 18, '2017-06-06', '2017-11-28',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-11-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 409;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 409;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 409;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 410
DO $$
DECLARE
    new_cid bigint := 5257949;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 410, 'RTC', 130019, 18, '2017-06-13', '2017-12-05',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-12-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 410;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 410;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 410;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 411
DO $$
DECLARE
    new_cid bigint := 5257950;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 411, 'RTC', 130019, 18, '2017-06-20', '2017-12-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-12-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 411;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 411;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 411;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 412
DO $$
DECLARE
    new_cid bigint := 5257951;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 412, 'RTC', 130019, 18, '2017-06-20', '2017-12-12',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2017-12-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 412;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 412;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 412;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 414
DO $$
DECLARE
    new_cid bigint := 5257952;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 414, 'RTC', 130019, 18, '2017-07-25', '2018-01-16',
        18000.00, 18000.00, 0.0, 720.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-01-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 414;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 414;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 414;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 415
DO $$
DECLARE
    new_cid bigint := 5257953;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 415, 'RTC', 130019, 18, '2017-08-29', '2018-02-20',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-02-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 415;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 415;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 415;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 416
DO $$
DECLARE
    new_cid bigint := 5257954;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 416, 'RTC', 130019, 18, '2017-08-29', '2018-02-20',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-02-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 416;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 416;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 416;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 417
DO $$
DECLARE
    new_cid bigint := 5257955;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 417, 'RTC', 130019, 18, '2017-09-19', '2018-03-13',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-03-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 417;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 417;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 417;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 418
DO $$
DECLARE
    new_cid bigint := 5257956;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 418, 'RTC', 130019, 18, '2017-09-26', '2018-03-20',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-03-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 418;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 418;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 418;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 419
DO $$
DECLARE
    new_cid bigint := 5257957;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 419, 'RTC', 130019, 18, '2017-10-03', '2018-03-27',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-03-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 419;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 419;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 419;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 420
DO $$
DECLARE
    new_cid bigint := 5257958;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 420, 'RTC', 130019, 18, '2017-10-03', '2018-03-27',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-03-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 420;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 420;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 420;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 421
DO $$
DECLARE
    new_cid bigint := 5257959;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 421, 'RTC', 130019, 18, '2017-10-03', '2018-03-27',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-03-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 421;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 421;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 421;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 422
DO $$
DECLARE
    new_cid bigint := 5257960;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 422, 'RTC', 130019, 18, '2017-10-10', '2018-04-03',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-04-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 422;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 422;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 422;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 423
DO $$
DECLARE
    new_cid bigint := 5257961;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 423, 'RTC', 130019, 18, '2017-10-24', '2018-04-17',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-04-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 423;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 423;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 423;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 424
DO $$
DECLARE
    new_cid bigint := 5257962;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 424, 'RTC', 130019, 18, '2017-11-28', '2018-05-22',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-05-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 424;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 424;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 424;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 425
DO $$
DECLARE
    new_cid bigint := 5257963;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 425, 'RTC', 130019, 18, '2017-12-05', '2018-05-29',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-05-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 425;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 425;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 425;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 426
DO $$
DECLARE
    new_cid bigint := 5257964;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 426, 'RTC', 130019, 18, '2017-12-05', '2018-05-29',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-05-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 426;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 426;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 426;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 427
DO $$
DECLARE
    new_cid bigint := 5257965;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 427, 'RTC', 130019, 18, '2017-12-12', '2018-06-05',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-06-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 427;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 427;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 427;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 428
DO $$
DECLARE
    new_cid bigint := 5257966;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 428, 'RTC', 130019, 18, '2017-12-19', '2018-06-12',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-06-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 428;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 428;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 428;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 429
DO $$
DECLARE
    new_cid bigint := 5257967;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 429, 'RTC', 130019, 18, '2018-01-30', '2018-07-24',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-07-24', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 429;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 429;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 429;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 430
DO $$
DECLARE
    new_cid bigint := 5257968;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 430, 'RTC', 130019, 18, '2018-02-06', '2018-07-31',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-07-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 430;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 430;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 430;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 431
DO $$
DECLARE
    new_cid bigint := 5257969;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 431, 'RTC', 130019, 18, '2018-02-06', '2018-07-31',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-07-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 431;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 431;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 431;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 432
DO $$
DECLARE
    new_cid bigint := 5257970;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 432, 'RTC', 130019, 18, '2018-02-13', '2018-08-07',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-08-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 432;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 432;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 432;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 433
DO $$
DECLARE
    new_cid bigint := 5257971;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 433, 'RTC', 130019, 18, '2018-02-20', '2018-08-14',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-08-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 433;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 433;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 433;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 434
DO $$
DECLARE
    new_cid bigint := 5257972;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 434, 'RTC', 130019, 18, '2018-02-20', '2018-08-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-08-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 434;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 434;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 434;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 435
DO $$
DECLARE
    new_cid bigint := 5257973;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 435, 'RTC', 130019, 18, '2018-03-06', '2018-08-28',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-08-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 435;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 435;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 435;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 436
DO $$
DECLARE
    new_cid bigint := 5257974;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 436, 'RTC', 130019, 18, '2018-03-13', '2018-09-04',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-09-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 436;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 436;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 436;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 437
DO $$
DECLARE
    new_cid bigint := 5257975;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 437, 'RTC', 130019, 18, '2018-03-27', '2018-09-18',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-09-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 437;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 437;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 437;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 438
DO $$
DECLARE
    new_cid bigint := 5257976;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 438, 'RTC', 130019, 18, '2018-04-03', '2018-09-25',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 438;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 438;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 438;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 439
DO $$
DECLARE
    new_cid bigint := 5257977;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 439, 'RTC', 130019, 18, '2018-04-03', '2018-09-25',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-09-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 439;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 439;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 439;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 440
DO $$
DECLARE
    new_cid bigint := 5257978;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 440, 'RTC', 130019, 18, '2018-04-17', '2018-10-09',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-10-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 440;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 440;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 440;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 441
DO $$
DECLARE
    new_cid bigint := 5257979;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 441, 'RTC', 130019, 18, '2018-04-24', '2018-10-16',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-10-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 441;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 441;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 441;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 442
DO $$
DECLARE
    new_cid bigint := 5257980;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 442, 'RTC', 130019, 18, '2018-05-29', '2018-11-20',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-11-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 442;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 442;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 442;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 443
DO $$
DECLARE
    new_cid bigint := 5257981;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 443, 'RTC', 130019, 18, '2018-06-05', '2018-11-27',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-11-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 443;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 443;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 443;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 444
DO $$
DECLARE
    new_cid bigint := 5257982;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 444, 'RTC', 130019, 18, '2018-06-05', '2018-11-27',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-11-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 444;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 444;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 444;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 445
DO $$
DECLARE
    new_cid bigint := 5257983;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 445, 'RTC', 130019, 18, '2018-06-05', '2018-11-27',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-11-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 445;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 445;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 445;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 446
DO $$
DECLARE
    new_cid bigint := 5257984;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 446, 'RTC', 130019, 18, '2018-06-26', '2018-12-18',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2018-12-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 446;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 446;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 446;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 447
DO $$
DECLARE
    new_cid bigint := 5257985;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 447, 'RTC', 130019, 18, '2018-07-10', '2019-01-01',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-01-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 447;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 447;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 447;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 448
DO $$
DECLARE
    new_cid bigint := 5257986;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 448, 'RTC', 130019, 18, '2018-07-10', '2019-01-01',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-01-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 448;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 448;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 448;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 449
DO $$
DECLARE
    new_cid bigint := 5257987;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 449, 'RTC', 130019, 18, '2018-07-10', '2019-01-01',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-01-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 449;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 449;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 449;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 450
DO $$
DECLARE
    new_cid bigint := 5257988;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 450, 'RTC', 130019, 18, '2018-07-24', '2019-01-15',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-01-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 450;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 450;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 450;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 451
DO $$
DECLARE
    new_cid bigint := 5257989;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 451, 'RTC', 130019, 18, '2018-07-24', '2019-01-15',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-01-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 451;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 451;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 451;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 452
DO $$
DECLARE
    new_cid bigint := 5257990;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 452, 'RTC', 130019, 18, '2018-07-31', '2019-01-22',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-01-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 452;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 452;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 452;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 453
DO $$
DECLARE
    new_cid bigint := 5257991;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 453, 'RTC', 130019, 18, '2018-08-14', '2019-02-05',
        15000.00, 15000.00, 0.0, 600.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-02-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 453;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 453;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 453;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 454
DO $$
DECLARE
    new_cid bigint := 5257992;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 454, 'RTC', 130019, 18, '2018-08-14', '2019-02-05',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-02-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 454;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 454;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 454;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 455
DO $$
DECLARE
    new_cid bigint := 5257993;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 455, 'RTC', 130019, 18, '2018-09-11', '2019-03-05',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-03-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 455;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 455;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 455;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 456
DO $$
DECLARE
    new_cid bigint := 5257994;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 456, 'RTC', 130019, 18, '2018-09-11', '2019-03-05',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-03-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 456;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 456;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 456;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 457
DO $$
DECLARE
    new_cid bigint := 5257995;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 457, 'RTC', 130019, 18, '2018-09-25', '2019-03-19',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-03-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 457;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 457;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 457;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 458
DO $$
DECLARE
    new_cid bigint := 5257996;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 458, 'RTC', 130019, 18, '2018-10-02', '2019-03-26',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-03-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 458;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 458;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 458;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 459
DO $$
DECLARE
    new_cid bigint := 5257997;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 459, 'RTC', 130019, 18, '2018-10-23', '2019-04-16',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-04-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 459;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 459;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 459;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 460
DO $$
DECLARE
    new_cid bigint := 5257998;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 460, 'RTC', 130019, 18, '2018-10-30', '2019-04-23',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-04-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 460;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 460;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 460;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 462
DO $$
DECLARE
    new_cid bigint := 5257999;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 462, 'RTC', 130019, 18, '2018-11-13', '2019-05-07',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-05-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 462;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 462;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 462;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 463
DO $$
DECLARE
    new_cid bigint := 5258000;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 463, 'RTC', 130019, 18, '2018-11-20', '2019-05-14',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-05-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 463;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 463;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 463;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 464
DO $$
DECLARE
    new_cid bigint := 5258001;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 464, 'RTC', 130019, 18, '2018-11-27', '2019-05-21',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-05-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 464;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 464;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 464;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 465
DO $$
DECLARE
    new_cid bigint := 5258002;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 465, 'RTC', 130019, 18, '2018-12-04', '2019-05-28',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-05-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 465;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 465;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 465;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 466
DO $$
DECLARE
    new_cid bigint := 5258003;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 466, 'RTC', 130019, 18, '2018-12-04', '2019-05-28',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-05-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 466;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 466;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 466;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 467
DO $$
DECLARE
    new_cid bigint := 5258004;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 467, 'RTC', 130019, 18, '2018-12-11', '2019-06-04',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-06-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 467;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 467;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 467;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 468
DO $$
DECLARE
    new_cid bigint := 5258005;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 468, 'RTC', 130019, 18, '2018-12-25', '2019-06-18',
        36000.00, 36000.00, 0.0, 1440.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-06-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 468;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 468;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 468;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 469
DO $$
DECLARE
    new_cid bigint := 5258006;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 469, 'RTC', 130019, 18, '2018-12-25', '2019-06-18',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-06-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 469;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 469;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 469;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 470
DO $$
DECLARE
    new_cid bigint := 5258007;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 470, 'RTC', 130019, 18, '2019-01-08', '2019-07-02',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-07-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 470;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 470;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 470;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 471
DO $$
DECLARE
    new_cid bigint := 5258008;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 471, 'RTC', 130019, 18, '2019-01-15', '2019-07-09',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-07-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 471;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 471;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 471;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 472
DO $$
DECLARE
    new_cid bigint := 5258009;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 472, 'RTC', 130019, 18, '2019-01-15', '2019-07-09',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-07-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 472;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 472;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 472;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 473
DO $$
DECLARE
    new_cid bigint := 5258010;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 473, 'RTC', 130019, 18, '2019-02-12', '2019-08-06',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-08-06', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 473;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 473;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 473;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 474
DO $$
DECLARE
    new_cid bigint := 5258011;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 474, 'RTC', 130019, 18, '2019-02-12', '2019-08-06',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-08-06', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 474;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 474;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 474;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 475
DO $$
DECLARE
    new_cid bigint := 5258012;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 475, 'RTC', 130019, 18, '2019-02-12', '2019-08-06',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-08-06', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 475;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 475;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 475;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 476
DO $$
DECLARE
    new_cid bigint := 5258013;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 476, 'RTC', 130019, 18, '2019-02-19', '2019-08-13',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-08-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 476;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 476;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 476;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 477
DO $$
DECLARE
    new_cid bigint := 5258014;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 477, 'RTC', 130019, 18, '2019-03-05', '2019-08-27',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-08-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 477;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 477;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 477;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 478
DO $$
DECLARE
    new_cid bigint := 5258015;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 478, 'RTC', 130019, 18, '2019-03-26', '2019-09-17',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 478;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 478;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 478;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 479
DO $$
DECLARE
    new_cid bigint := 5258016;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 479, 'RTC', 130019, 18, '2019-06-04', '2019-11-26',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-11-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 479;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 479;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 479;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 480
DO $$
DECLARE
    new_cid bigint := 5258017;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 480, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 480;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 480;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 480;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 481
DO $$
DECLARE
    new_cid bigint := 5258018;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 481, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 481;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 481;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 481;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 482
DO $$
DECLARE
    new_cid bigint := 5258019;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 482, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 482;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 482;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 482;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 483
DO $$
DECLARE
    new_cid bigint := 5258020;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 483, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 483;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 483;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 483;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 484
DO $$
DECLARE
    new_cid bigint := 5258021;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 484, 'RTC', 130019, 18, '2019-05-28', '2019-11-19',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-11-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 484;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 484;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 484;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 485
DO $$
DECLARE
    new_cid bigint := 5258022;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 485, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 485;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 485;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 485;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 486
DO $$
DECLARE
    new_cid bigint := 5258023;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 486, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 486;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 486;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 486;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 487
DO $$
DECLARE
    new_cid bigint := 5258024;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 487, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 487;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 487;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 487;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 488
DO $$
DECLARE
    new_cid bigint := 5258025;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 488, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 488;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 488;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 488;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 489
DO $$
DECLARE
    new_cid bigint := 5258026;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 489, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 489;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 489;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 489;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 490
DO $$
DECLARE
    new_cid bigint := 5258027;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 490, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 490;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 490;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 490;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 491
DO $$
DECLARE
    new_cid bigint := 5258028;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 491, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 491;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 491;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 491;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 492
DO $$
DECLARE
    new_cid bigint := 5258029;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 492, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        87500.00, 87500.00, 0.0, 3500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 492;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 492;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 492;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 493
DO $$
DECLARE
    new_cid bigint := 5258030;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 493, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 493;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 493;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 493;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 494
DO $$
DECLARE
    new_cid bigint := 5258031;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 494, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 494;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 494;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 494;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 495
DO $$
DECLARE
    new_cid bigint := 5258032;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 495, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 495;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 495;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 495;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 496
DO $$
DECLARE
    new_cid bigint := 5258033;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 496, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 496;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 496;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 496;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 497
DO $$
DECLARE
    new_cid bigint := 5258034;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 497, 'RTC', 130019, 18, '2019-03-10', '2019-09-01',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2019-09-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 497;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 497;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 497;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 499
DO $$
DECLARE
    new_cid bigint := 5258035;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 499, 'RTC', 130019, 18, '2019-10-01', '2020-03-24',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-03-24', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 499;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 499;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 499;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 500
DO $$
DECLARE
    new_cid bigint := 5258036;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 500, 'RTC', 130019, 18, '2019-10-01', '2020-03-24',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-03-24', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 500;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 500;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 500;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 501
DO $$
DECLARE
    new_cid bigint := 5258037;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 501, 'RTC', 130019, 18, '2019-10-08', '2020-03-31',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-03-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 501;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 501;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 501;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 502
DO $$
DECLARE
    new_cid bigint := 5258038;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 502, 'RTC', 130019, 18, '2019-10-08', '2020-03-31',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-03-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 502;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 502;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 502;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 503
DO $$
DECLARE
    new_cid bigint := 5258039;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 503, 'RTC', 130019, 18, '2019-10-15', '2020-04-07',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-04-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 503;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 503;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 503;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 504
DO $$
DECLARE
    new_cid bigint := 5258040;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 504, 'RTC', 130019, 18, '2019-10-22', '2020-04-14',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-04-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 504;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 504;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 504;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 505
DO $$
DECLARE
    new_cid bigint := 5258041;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 505, 'RTC', 130019, 18, '2019-10-29', '2020-04-21',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-04-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 505;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 505;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 505;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 506
DO $$
DECLARE
    new_cid bigint := 5258042;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 506, 'RTC', 130019, 18, '2019-10-29', '2020-04-21',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-04-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 506;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 506;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 506;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 507
DO $$
DECLARE
    new_cid bigint := 5258043;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 507, 'RTC', 130019, 18, '2019-11-05', '2020-04-28',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-04-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 507;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 507;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 507;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 508
DO $$
DECLARE
    new_cid bigint := 5258044;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 508, 'RTC', 130019, 18, '2019-11-05', '2020-04-28',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-04-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 508;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 508;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 508;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 509
DO $$
DECLARE
    new_cid bigint := 5258045;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 509, 'RTC', 130019, 18, '2019-11-19', '2020-05-12',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 509;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 509;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 509;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 510
DO $$
DECLARE
    new_cid bigint := 5258046;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 510, 'RTC', 130019, 18, '2019-11-19', '2020-05-12',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-05-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 510;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 510;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 510;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 511
DO $$
DECLARE
    new_cid bigint := 5258047;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 511, 'RTC', 130019, 18, '2019-12-03', '2020-05-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 511;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 511;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 511;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 512
DO $$
DECLARE
    new_cid bigint := 5258048;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 512, 'RTC', 130019, 18, '2019-12-03', '2020-05-26',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-05-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 512;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 512;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 512;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 513
DO $$
DECLARE
    new_cid bigint := 5258049;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 513, 'RTC', 130019, 18, '2019-12-10', '2020-06-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-06-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 513;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 513;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 513;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 515
DO $$
DECLARE
    new_cid bigint := 5258050;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 515, 'RTC', 130019, 18, '2019-12-24', '2020-06-16',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 515;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 515;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 515;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 516
DO $$
DECLARE
    new_cid bigint := 5258051;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 516, 'RTC', 130019, 18, '2019-12-24', '2020-06-16',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 516;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 516;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 516;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 517
DO $$
DECLARE
    new_cid bigint := 5258052;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 517, 'RTC', 130019, 18, '2019-12-24', '2020-06-16',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-06-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 517;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 517;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 517;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 518
DO $$
DECLARE
    new_cid bigint := 5258053;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 518, 'RTC', 130019, 18, '2019-12-28', '2020-06-20',
        6250.00, 6250.00, 0.0, 250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-06-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 518;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 518;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 518;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 519
DO $$
DECLARE
    new_cid bigint := 5258054;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 519, 'RTC', 130019, 18, '2020-01-14', '2020-07-07',
        87500.00, 87500.00, 0.0, 3500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-07-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 519;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 519;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 519;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 520
DO $$
DECLARE
    new_cid bigint := 5258055;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 520, 'RTC', 130019, 18, '2019-12-28', '2020-06-20',
        125000.00, 125000.00, 0.0, 5000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-06-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 520;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 520;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 520;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 521
DO $$
DECLARE
    new_cid bigint := 5258056;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 521, 'RTC', 130019, 18, '2019-12-28', '2020-06-20',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-06-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 521;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 521;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 521;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 523
DO $$
DECLARE
    new_cid bigint := 5258057;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 523, 'RTC', 130019, 18, '2019-12-28', '2020-06-20',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-06-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 523;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 523;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 523;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 524
DO $$
DECLARE
    new_cid bigint := 5258058;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 524, 'RTC', 130019, 18, '2020-02-04', '2020-07-28',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-07-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 524;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 524;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 524;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 526
DO $$
DECLARE
    new_cid bigint := 5258059;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 526, 'RTC', 130019, 18, '2020-02-18', '2020-08-11',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-08-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 526;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 526;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 526;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 527
DO $$
DECLARE
    new_cid bigint := 5258060;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 527, 'RTC', 130019, 18, '2020-02-18', '2020-08-11',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-08-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 527;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 527;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 527;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 529
DO $$
DECLARE
    new_cid bigint := 5258061;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 529, 'RTC', 130019, 18, '2020-06-09', '2020-12-01',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-12-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 529;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 529;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 529;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 530
DO $$
DECLARE
    new_cid bigint := 5258062;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 530, 'RTC', 130019, 18, '2020-06-09', '2020-12-01',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-12-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 530;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 530;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 530;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 531
DO $$
DECLARE
    new_cid bigint := 5258063;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 531, 'RTC', 130019, 18, '2020-06-09', '2020-12-01',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-12-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 531;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 531;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 531;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 532
DO $$
DECLARE
    new_cid bigint := 5258064;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 532, 'RTC', 130019, 18, '2020-06-23', '2020-12-15',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-12-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 532;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 532;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 532;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 533
DO $$
DECLARE
    new_cid bigint := 5258065;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 533, 'RTC', 130019, 18, '2020-06-30', '2020-12-22',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-12-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 533;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 533;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 533;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 534
DO $$
DECLARE
    new_cid bigint := 5258066;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 534, 'RTC', 130019, 18, '2020-07-07', '2020-12-29',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-12-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 534;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 534;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 534;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 535
DO $$
DECLARE
    new_cid bigint := 5258067;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 535, 'RTC', 130019, 18, '2020-07-07', '2020-12-29',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2020-12-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 535;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 535;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 535;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 536
DO $$
DECLARE
    new_cid bigint := 5258068;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 536, 'RTC', 130019, 18, '2020-07-21', '2021-01-12',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-01-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 536;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 536;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 536;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 537
DO $$
DECLARE
    new_cid bigint := 5258069;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 537, 'RTC', 130019, 18, '2020-07-28', '2021-01-19',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-01-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 537;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 537;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 537;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 538
DO $$
DECLARE
    new_cid bigint := 5258070;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 538, 'RTC', 130019, 18, '2020-08-25', '2021-02-16',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-02-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 538;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 538;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 538;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 539
DO $$
DECLARE
    new_cid bigint := 5258071;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 539, 'RTC', 130019, 18, '2021-12-07', '2022-05-31',
        100000.00, 100000.00, 0.0, 4000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-05-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 539;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 539;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 539;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 540
DO $$
DECLARE
    new_cid bigint := 5258072;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 540, 'RTC', 130019, 18, '2020-09-01', '2021-02-23',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-02-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 540;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 540;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 540;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 541
DO $$
DECLARE
    new_cid bigint := 5258073;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 541, 'RTC', 130019, 18, '2020-09-08', '2021-03-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-03-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 541;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 541;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 541;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 542
DO $$
DECLARE
    new_cid bigint := 5258074;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 542, 'RTC', 130019, 18, '2020-09-08', '2021-03-02',
        125000.00, 125000.00, 0.0, 5000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-03-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 542;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 542;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 542;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 543
DO $$
DECLARE
    new_cid bigint := 5258075;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 543, 'RTC', 130019, 18, '2020-09-15', '2021-03-09',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-03-09', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 543;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 543;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 543;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 544
DO $$
DECLARE
    new_cid bigint := 5258076;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 544, 'RTC', 130019, 18, '2020-10-06', '2021-03-30',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-03-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 544;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 544;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 544;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 545
DO $$
DECLARE
    new_cid bigint := 5258077;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 545, 'RTC', 130019, 18, '2020-10-06', '2021-03-30',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-03-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 545;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 545;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 545;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 546
DO $$
DECLARE
    new_cid bigint := 5258078;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 546, 'RTC', 130019, 18, '2020-11-10', '2021-05-04',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-05-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 546;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 546;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 546;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 547
DO $$
DECLARE
    new_cid bigint := 5258079;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 547, 'RTC', 130019, 18, '2020-11-17', '2021-05-11',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-05-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 547;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 547;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 547;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 548
DO $$
DECLARE
    new_cid bigint := 5258080;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 548, 'RTC', 130019, 18, '2020-11-24', '2021-05-18',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-05-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 548;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 548;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 548;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 549
DO $$
DECLARE
    new_cid bigint := 5258081;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 549, 'RTC', 130019, 18, '2020-12-08', '2021-06-01',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-06-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 549;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 549;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 549;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 550
DO $$
DECLARE
    new_cid bigint := 5258082;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 550, 'RTC', 130019, 18, '2020-12-08', '2021-06-01',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-06-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 550;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 550;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 550;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 551
DO $$
DECLARE
    new_cid bigint := 5258083;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 551, 'RTC', 130019, 18, '2020-12-08', '2021-06-01',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-06-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 551;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 551;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 551;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 552
DO $$
DECLARE
    new_cid bigint := 5258084;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 552, 'RTC', 130019, 18, '2020-12-22', '2021-06-15',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-06-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 552;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 552;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 552;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 553
DO $$
DECLARE
    new_cid bigint := 5258085;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 553, 'RTC', 130019, 18, '2020-12-15', '2021-06-08',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-06-08', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 553;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 553;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 553;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 554
DO $$
DECLARE
    new_cid bigint := 5258086;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 554, 'RTC', 130019, 18, '2020-12-29', '2021-06-22',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-06-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 554;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 554;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 554;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 555
DO $$
DECLARE
    new_cid bigint := 5258087;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 555, 'RTC', 130019, 18, '2020-12-29', '2021-06-22',
        6250.00, 6250.00, 0.0, 250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-06-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 555;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 555;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 555;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 556
DO $$
DECLARE
    new_cid bigint := 5258088;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 556, 'RTC', 130019, 18, '2021-01-26', '2021-07-20',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-07-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 556;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 556;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 556;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 557
DO $$
DECLARE
    new_cid bigint := 5258089;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 557, 'RTC', 130019, 18, '2021-01-26', '2021-07-20',
        125000.00, 125000.00, 0.0, 5000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-07-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 557;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 557;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 557;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 558
DO $$
DECLARE
    new_cid bigint := 5258090;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 558, 'RTC', 130019, 18, '2021-01-26', '2021-07-20',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-07-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 558;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 558;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 558;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 559
DO $$
DECLARE
    new_cid bigint := 5258091;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 559, 'RTC', 130019, 18, '2021-02-16', '2021-08-10',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-08-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 559;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 559;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 559;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 560
DO $$
DECLARE
    new_cid bigint := 5258092;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 560, 'RTC', 130019, 18, '2021-02-23', '2021-08-17',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-08-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 560;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 560;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 560;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 561
DO $$
DECLARE
    new_cid bigint := 5258093;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 561, 'RTC', 130019, 18, '2021-02-23', '2021-08-17',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-08-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 561;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 561;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 561;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 562
DO $$
DECLARE
    new_cid bigint := 5258094;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 562, 'RTC', 130019, 18, '2021-03-02', '2021-08-24',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-08-24', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 562;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 562;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 562;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 563
DO $$
DECLARE
    new_cid bigint := 5258095;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 563, 'RTC', 130019, 18, '2021-03-09', '2021-08-31',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-08-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 563;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 563;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 563;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 564
DO $$
DECLARE
    new_cid bigint := 5258096;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 564, 'RTC', 130019, 18, '2021-03-16', '2021-09-07',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-09-07', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 564;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 564;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 564;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 565
DO $$
DECLARE
    new_cid bigint := 5258097;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 565, 'RTC', 130019, 18, '2021-03-30', '2021-09-21',
        100000.00, 100000.00, 0.0, 4000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2021-09-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 565;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 565;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 565;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 566
DO $$
DECLARE
    new_cid bigint := 5258098;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 566, 'RTC', 130019, 18, '2021-07-13', '2022-01-04',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 566;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 566;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 566;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 567
DO $$
DECLARE
    new_cid bigint := 5258099;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 567, 'RTC', 130019, 18, '2021-07-13', '2022-01-04',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 567;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 567;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 567;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 568
DO $$
DECLARE
    new_cid bigint := 5258100;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 568, 'RTC', 130019, 18, '2021-07-13', '2022-01-04',
        6250.00, 6250.00, 0.0, 250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 568;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 568;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 568;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 569
DO $$
DECLARE
    new_cid bigint := 5258101;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 569, 'RTC', 130019, 18, '2021-07-13', '2022-01-04',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 569;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 569;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 569;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 570
DO $$
DECLARE
    new_cid bigint := 5258102;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 570, 'RTC', 130019, 18, '2021-07-20', '2022-01-11',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 570;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 570;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 570;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 571
DO $$
DECLARE
    new_cid bigint := 5258103;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 571, 'RTC', 130019, 18, '2021-07-27', '2022-01-18',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 571;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 571;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 571;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 572
DO $$
DECLARE
    new_cid bigint := 5258104;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 572, 'RTC', 130019, 18, '2021-07-27', '2022-01-18',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 572;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 572;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 572;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 573
DO $$
DECLARE
    new_cid bigint := 5258105;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 573, 'RTC', 130019, 18, '2021-07-27', '2022-01-18',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 573;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 573;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 573;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 574
DO $$
DECLARE
    new_cid bigint := 5258106;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 574, 'RTC', 130019, 18, '2021-08-03', '2022-01-25',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 574;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 574;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 574;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 575
DO $$
DECLARE
    new_cid bigint := 5258107;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 575, 'RTC', 130019, 18, '2021-08-03', '2022-01-25',
        150000.00, 150000.00, 0.0, 6000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 575;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 575;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 575;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 576
DO $$
DECLARE
    new_cid bigint := 5258108;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 576, 'RTC', 130019, 18, '2021-08-03', '2022-01-25',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-01-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 576;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 576;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 576;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 577
DO $$
DECLARE
    new_cid bigint := 5258109;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 577, 'RTC', 130019, 18, '2021-09-28', '2022-03-22',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-03-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 577;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 577;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 577;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 578
DO $$
DECLARE
    new_cid bigint := 5258110;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 578, 'RTC', 130019, 18, '2021-10-05', '2022-03-29',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-03-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 578;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 578;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 578;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 579
DO $$
DECLARE
    new_cid bigint := 5258111;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 579, 'RTC', 130019, 18, '2021-10-05', '2022-03-29',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-03-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 579;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 579;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 579;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 580
DO $$
DECLARE
    new_cid bigint := 5258112;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 580, 'RTC', 130019, 18, '2021-10-12', '2022-04-05',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-04-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 580;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 580;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 580;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 581
DO $$
DECLARE
    new_cid bigint := 5258113;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 581, 'RTC', 130019, 18, '2021-11-02', '2022-04-26',
        100000.00, 100000.00, 0.0, 4000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-04-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 581;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 581;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 581;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 582
DO $$
DECLARE
    new_cid bigint := 5258114;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 582, 'RTC', 130019, 18, '2021-11-02', '2022-04-26',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-04-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 582;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 582;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 582;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 583
DO $$
DECLARE
    new_cid bigint := 5258115;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 583, 'RTC', 130019, 18, '2021-12-07', '2022-05-31',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-05-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 583;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 583;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 583;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 584
DO $$
DECLARE
    new_cid bigint := 5258116;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 584, 'RTC', 130019, 18, '2021-12-07', '2022-05-31',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-05-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 584;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 584;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 584;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 586
DO $$
DECLARE
    new_cid bigint := 5258117;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 586, 'RTC', 130019, 18, '2021-12-21', '2022-06-14',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-06-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 586;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 586;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 586;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 587
DO $$
DECLARE
    new_cid bigint := 5258118;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 587, 'RTC', 130019, 18, '2022-01-01', '2022-06-25',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-06-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 587;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 587;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 587;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 588
DO $$
DECLARE
    new_cid bigint := 5258119;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 588, 'RTC', 130019, 18, '2022-01-01', '2022-06-25',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-06-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 588;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 588;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 588;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 589
DO $$
DECLARE
    new_cid bigint := 5258120;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 589, 'RTC', 130019, 18, '2022-01-01', '2022-06-25',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-06-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 589;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 589;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 589;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 590
DO $$
DECLARE
    new_cid bigint := 5258121;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 590, 'RTC', 130019, 18, '2022-01-01', '2022-06-25',
        18760.00, 18760.00, 0.0, 750.40,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-06-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 590;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 590;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 590;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 591
DO $$
DECLARE
    new_cid bigint := 5258122;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 591, 'RTC', 130019, 18, '2022-01-01', '2022-06-25',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-06-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 591;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 591;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 591;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 592
DO $$
DECLARE
    new_cid bigint := 5258123;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 592, 'RTC', 130019, 18, '2022-01-01', '2022-06-25',
        150000.00, 150000.00, 0.0, 6000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-06-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 592;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 592;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 592;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 593
DO $$
DECLARE
    new_cid bigint := 5258124;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 593, 'RTC', 130019, 18, '2022-01-01', '2022-06-25',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-06-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 593;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 593;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 593;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 594
DO $$
DECLARE
    new_cid bigint := 5258125;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 594, 'RTC', 130019, 18, '2022-03-08', '2022-08-30',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-08-30', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 594;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 594;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 594;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 595
DO $$
DECLARE
    new_cid bigint := 5258126;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 595, 'RTC', 130019, 18, '2022-03-15', '2022-09-06',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-09-06', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 595;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 595;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 595;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 596
DO $$
DECLARE
    new_cid bigint := 5258127;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 596, 'RTC', 130019, 18, '2022-03-22', '2022-09-13',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-09-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 596;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 596;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 596;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 597
DO $$
DECLARE
    new_cid bigint := 5258128;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 597, 'RTC', 130019, 18, '2022-03-29', '2022-09-20',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-09-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 597;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 597;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 597;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 598
DO $$
DECLARE
    new_cid bigint := 5258129;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 598, 'RTC', 130019, 18, '2022-04-05', '2022-09-27',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-09-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 598;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 598;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 598;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 599
DO $$
DECLARE
    new_cid bigint := 5258130;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 599, 'RTC', 130019, 18, '2022-04-19', '2022-10-11',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-10-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 599;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 599;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 599;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 600
DO $$
DECLARE
    new_cid bigint := 5258131;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 600, 'RTC', 130019, 18, '2022-04-19', '2022-10-11',
        100000.00, 100000.00, 0.0, 4000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-10-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 600;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 600;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 600;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 602
DO $$
DECLARE
    new_cid bigint := 5258132;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 602, 'RTC', 130019, 18, '2022-05-17', '2022-11-08',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-11-08', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 602;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 602;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 602;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 604
DO $$
DECLARE
    new_cid bigint := 5258133;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 604, 'RTC', 130019, 18, '2022-05-24', '2022-11-15',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-11-15', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 604;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 604;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 604;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 605
DO $$
DECLARE
    new_cid bigint := 5258134;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 605, 'RTC', 130019, 18, '2022-05-31', '2022-11-22',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-11-22', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 605;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 605;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 605;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 606
DO $$
DECLARE
    new_cid bigint := 5258135;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 606, 'RTC', 130019, 18, '2022-06-07', '2022-11-29',
        43750.00, 43750.00, 0.0, 1750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-11-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 606;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 606;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 606;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 607
DO $$
DECLARE
    new_cid bigint := 5258136;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 607, 'RTC', 130019, 18, '2022-06-14', '2022-12-06',
        187500.00, 187500.00, 0.0, 7500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-12-06', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 607;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 607;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 607;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 608
DO $$
DECLARE
    new_cid bigint := 5258137;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 608, 'RTC', 130019, 18, '2022-06-21', '2022-12-13',
        100000.00, 100000.00, 0.0, 4000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-12-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 608;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 608;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 608;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 609
DO $$
DECLARE
    new_cid bigint := 5258138;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 609, 'RTC', 130019, 18, '2022-07-05', '2022-12-27',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2022-12-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 609;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 609;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 609;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 610
DO $$
DECLARE
    new_cid bigint := 5258139;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 610, 'RTC', 130019, 18, '2022-07-19', '2023-01-10',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-01-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 610;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 610;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 610;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 611
DO $$
DECLARE
    new_cid bigint := 5258140;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 611, 'RTC', 130019, 18, '2022-07-26', '2023-01-17',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-01-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 611;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 611;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 611;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 612
DO $$
DECLARE
    new_cid bigint := 5258141;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 612, 'RTC', 130019, 18, '2022-07-26', '2023-01-17',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-01-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 612;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 612;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 612;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 613
DO $$
DECLARE
    new_cid bigint := 5258142;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 613, 'RTC', 130019, 18, '2022-08-02', '2023-01-24',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-01-24', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 613;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 613;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 613;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 614
DO $$
DECLARE
    new_cid bigint := 5258143;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 614, 'RTC', 130019, 18, '2022-08-02', '2023-01-24',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-01-24', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 614;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 614;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 614;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 615
DO $$
DECLARE
    new_cid bigint := 5258144;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 615, 'RTC', 130019, 18, '2022-08-30', '2023-02-21',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-02-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 615;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 615;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 615;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 616
DO $$
DECLARE
    new_cid bigint := 5258145;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 616, 'RTC', 130019, 18, '2022-08-30', '2023-02-21',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-02-21', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 616;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 616;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 616;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 617
DO $$
DECLARE
    new_cid bigint := 5258146;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 617, 'RTC', 130019, 18, '2022-09-20', '2023-03-14',
        125000.00, 125000.00, 0.0, 5000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-03-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 617;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 617;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 617;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 618
DO $$
DECLARE
    new_cid bigint := 5258147;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 618, 'RTC', 130019, 18, '2022-09-20', '2023-03-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-03-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 618;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 618;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 618;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 619
DO $$
DECLARE
    new_cid bigint := 5258148;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 619, 'RTC', 130019, 18, '2022-10-04', '2023-03-28',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-03-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 619;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 619;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 619;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 620
DO $$
DECLARE
    new_cid bigint := 5258149;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 620, 'RTC', 130019, 18, '2022-10-18', '2023-04-11',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-04-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 620;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 620;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 620;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 621
DO $$
DECLARE
    new_cid bigint := 5258150;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 621, 'RTC', 130019, 18, '2022-10-18', '2023-04-11',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-04-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 621;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 621;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 621;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 622
DO $$
DECLARE
    new_cid bigint := 5258151;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 622, 'RTC', 130019, 18, '2022-10-25', '2023-04-18',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-04-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 622;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 622;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 622;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 623
DO $$
DECLARE
    new_cid bigint := 5258152;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 623, 'RTC', 130019, 18, '2022-11-08', '2023-05-02',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-05-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 623;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 623;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 623;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 624
DO $$
DECLARE
    new_cid bigint := 5258153;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 624, 'RTC', 130019, 18, '2022-11-08', '2023-05-02',
        187500.00, 187500.00, 0.0, 7500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-05-02', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 624;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 624;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 624;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 626
DO $$
DECLARE
    new_cid bigint := 5258154;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 626, 'RTC', 130019, 18, '2022-11-22', '2023-05-16',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-05-16', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 626;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 626;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 626;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 627
DO $$
DECLARE
    new_cid bigint := 5258155;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 627, 'RTC', 130019, 18, '2022-12-13', '2023-06-06',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-06-06', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 627;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 627;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 627;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 628
DO $$
DECLARE
    new_cid bigint := 5258156;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 628, 'RTC', 130019, 18, '2022-12-20', '2023-06-13',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-06-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 628;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 628;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 628;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 629
DO $$
DECLARE
    new_cid bigint := 5258157;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 629, 'RTC', 130019, 18, '2022-12-27', '2023-06-20',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-06-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 629;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 629;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 629;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 630
DO $$
DECLARE
    new_cid bigint := 5258158;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 630, 'RTC', 130019, 18, '2023-01-03', '2023-06-27',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-06-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 630;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 630;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 630;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 631
DO $$
DECLARE
    new_cid bigint := 5258159;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 631, 'RTC', 130019, 18, '2023-01-10', '2023-07-04',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-07-04', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 631;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 631;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 631;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 632
DO $$
DECLARE
    new_cid bigint := 5258160;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 632, 'RTC', 130019, 18, '2023-01-17', '2023-07-11',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-07-11', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 632;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 632;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 632;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 633
DO $$
DECLARE
    new_cid bigint := 5258161;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 633, 'RTC', 130019, 18, '2023-01-31', '2023-07-25',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-07-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 633;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 633;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 633;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 634
DO $$
DECLARE
    new_cid bigint := 5258162;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 634, 'RTC', 130019, 18, '2023-02-07', '2023-08-01',
        6250.00, 6250.00, 0.0, 250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-08-01', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 634;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 634;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 634;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 636
DO $$
DECLARE
    new_cid bigint := 5258163;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 636, 'RTC', 130019, 18, '2023-03-07', '2023-08-29',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-08-29', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 636;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 636;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 636;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 637
DO $$
DECLARE
    new_cid bigint := 5258164;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 637, 'RTC', 130019, 18, '2023-03-14', '2023-09-05',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-09-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 637;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 637;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 637;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 638
DO $$
DECLARE
    new_cid bigint := 5258165;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 638, 'RTC', 130019, 18, '2023-03-21', '2023-09-12',
        125000.00, 125000.00, 0.0, 5000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-09-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 638;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 638;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 638;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 639
DO $$
DECLARE
    new_cid bigint := 5258166;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 639, 'RTC', 130019, 18, '2023-03-28', '2023-09-19',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-09-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 639;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 639;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 639;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 640
DO $$
DECLARE
    new_cid bigint := 5258167;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 640, 'RTC', 130019, 18, '2023-04-04', '2023-09-26',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-09-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 640;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 640;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 640;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 641
DO $$
DECLARE
    new_cid bigint := 5258168;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 641, 'RTC', 130019, 18, '2023-04-04', '2023-09-26',
        250000.00, 250000.00, 0.0, 10000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-09-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 641;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 641;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 641;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 642
DO $$
DECLARE
    new_cid bigint := 5258169;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 642, 'RTC', 130019, 18, '2023-04-11', '2023-10-03',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-10-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 642;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 642;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 642;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 645
DO $$
DECLARE
    new_cid bigint := 5258170;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 645, 'RTC', 130019, 18, '2023-06-13', '2023-12-05',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-12-05', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 645;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 645;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 645;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 646
DO $$
DECLARE
    new_cid bigint := 5258171;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 646, 'RTC', 130019, 18, '2023-06-20', '2023-12-12',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-12-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 646;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 646;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 646;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 647
DO $$
DECLARE
    new_cid bigint := 5258172;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 647, 'RTC', 130019, 18, '2023-06-27', '2023-12-19',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-12-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 647;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 647;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 647;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 649
DO $$
DECLARE
    new_cid bigint := 5258173;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 649, 'RTC', 130019, 18, '2023-06-27', '2023-12-19',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-12-19', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 649;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 649;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 649;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 650
DO $$
DECLARE
    new_cid bigint := 5258174;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 650, 'RTC', 130019, 18, '2023-07-04', '2023-12-26',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-12-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 650;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 650;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 650;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 651
DO $$
DECLARE
    new_cid bigint := 5258175;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 651, 'RTC', 130019, 18, '2023-07-04', '2023-12-26',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2023-12-26', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 651;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 651;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 651;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 652
DO $$
DECLARE
    new_cid bigint := 5258176;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 652, 'RTC', 130019, 18, '2023-08-01', '2024-01-23',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-01-23', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 652;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 652;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 652;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 653
DO $$
DECLARE
    new_cid bigint := 5258177;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 653, 'RTC', 130019, 18, '2023-08-22', '2024-02-13',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-02-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 653;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 653;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 653;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 654
DO $$
DECLARE
    new_cid bigint := 5258178;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 654, 'RTC', 130019, 18, '2023-08-29', '2024-02-20',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-02-20', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 654;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 654;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 654;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 655
DO $$
DECLARE
    new_cid bigint := 5258179;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 655, 'RTC', 130019, 18, '2023-09-19', '2024-03-12',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-03-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 655;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 655;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 655;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 656
DO $$
DECLARE
    new_cid bigint := 5258180;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 656, 'RTC', 130019, 18, '2023-09-19', '2024-03-12',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-03-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 656;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 656;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 656;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 657
DO $$
DECLARE
    new_cid bigint := 5258181;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 657, 'RTC', 130019, 18, '2023-09-19', '2024-03-12',
        62500.00, 62500.00, 0.0, 2500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-03-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 657;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 657;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 657;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 658
DO $$
DECLARE
    new_cid bigint := 5258182;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 658, 'RTC', 130019, 18, '2023-09-19', '2024-03-12',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-03-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 658;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 658;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 658;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 659
DO $$
DECLARE
    new_cid bigint := 5258183;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 659, 'RTC', 130019, 18, '2023-09-19', '2024-03-12',
        250000.00, 250000.00, 0.0, 10000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-03-12', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 659;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 659;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 659;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 660
DO $$
DECLARE
    new_cid bigint := 5258184;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 660, 'RTC', 130019, 18, '2023-11-21', '2024-05-14',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-05-14', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 660;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 660;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 660;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 661
DO $$
DECLARE
    new_cid bigint := 5258185;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 661, 'RTC', 130019, 18, '2023-12-05', '2024-05-28',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-05-28', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 661;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 661;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 661;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 662
DO $$
DECLARE
    new_cid bigint := 5258186;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 662, 'RTC', 130019, 18, '2023-12-26', '2024-06-18',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-06-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 662;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 662;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 662;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 663
DO $$
DECLARE
    new_cid bigint := 5258187;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 663, 'RTC', 130019, 18, '2023-12-26', '2024-06-18',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-06-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 663;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 663;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 663;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 664
DO $$
DECLARE
    new_cid bigint := 5258188;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 664, 'RTC', 130019, 18, '2023-12-26', '2024-06-18',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-06-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 664;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 664;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 664;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 667
DO $$
DECLARE
    new_cid bigint := 5258189;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 667, 'RTC', 130019, 18, '2024-02-20', '2024-08-13',
        26000.00, 26000.00, 0.0, 1040.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-08-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 667;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 667;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 667;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 668
DO $$
DECLARE
    new_cid bigint := 5258190;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 668, 'RTC', 130019, 18, '2024-03-12', '2024-09-03',
        13000.00, 13000.00, 0.0, 520.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-09-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 668;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 668;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 668;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 669
DO $$
DECLARE
    new_cid bigint := 5258191;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 669, 'RTC', 130019, 18, '2024-03-12', '2024-09-03',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-09-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 669;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 669;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 669;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 670
DO $$
DECLARE
    new_cid bigint := 5258192;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 670, 'RTC', 130019, 18, '2024-03-19', '2024-09-10',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-09-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 670;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 670;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 670;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 671
DO $$
DECLARE
    new_cid bigint := 5258193;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 671, 'RTC', 130019, 18, '2024-03-19', '2024-09-10',
        31250.00, 31250.00, 0.0, 1250.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-09-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 671;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 671;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 671;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 672
DO $$
DECLARE
    new_cid bigint := 5258194;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 672, 'RTC', 130019, 18, '2024-06-11', '2024-12-03',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-12-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 672;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 672;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 672;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 673
DO $$
DECLARE
    new_cid bigint := 5258195;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 673, 'RTC', 130019, 18, '2024-06-11', '2024-12-03',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-12-03', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 673;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 673;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 673;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 675
DO $$
DECLARE
    new_cid bigint := 5258196;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 675, 'RTC', 130019, 18, '2024-06-25', '2024-12-17',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-12-17', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 675;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 675;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 675;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 676
DO $$
DECLARE
    new_cid bigint := 5258197;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 676, 'RTC', 130019, 18, '2024-07-09', '2024-12-31',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2024-12-31', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 676;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 676;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 676;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 677
DO $$
DECLARE
    new_cid bigint := 5258198;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 677, 'RTC', 130019, 18, '2024-08-27', '2025-02-18',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2025-02-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 677;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 677;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 677;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 678
DO $$
DECLARE
    new_cid bigint := 5258199;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 678, 'RTC', 130019, 18, '2024-09-03', '2025-02-25',
        25000.00, 25000.00, 0.0, 1000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2025-02-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 678;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 678;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 678;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 679
DO $$
DECLARE
    new_cid bigint := 5258200;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 679, 'RTC', 130019, 18, '2024-09-03', '2025-02-25',
        37500.00, 37500.00, 0.0, 1500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2025-02-25', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 679;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 679;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 679;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 680
DO $$
DECLARE
    new_cid bigint := 5258201;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 680, 'RTC', 130019, 18, '2024-09-24', '2025-03-18',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2025-03-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 680;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 680;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 680;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 681
DO $$
DECLARE
    new_cid bigint := 5258202;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 681, 'RTC', 130019, 18, '2024-09-24', '2025-03-18',
        12500.00, 12500.00, 0.0, 500.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2025-03-18', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 681;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 681;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 681;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 682
DO $$
DECLARE
    new_cid bigint := 5258203;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 682, 'RTC', 130019, 18, '2024-11-19', '2025-05-13',
        75000.00, 75000.00, 0.0, 3000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2025-05-13', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 682;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 682;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 682;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 683
DO $$
DECLARE
    new_cid bigint := 5258204;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 683, 'RTC', 130019, 18, '2024-12-03', '2025-05-27',
        50000.00, 50000.00, 0.0, 2000.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2025-05-27', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 683;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 683;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 683;
END $$;

-- Recreating customer for Village 'BHADRAVATHI' (ID: 130019), ANO: 684
DO $$
DECLARE
    new_cid bigint := 5258205;
BEGIN
    INSERT INTO historic_customer_data (
        cid, ano, name, vid, eid, start_date, end_date,
        total_amount, paid_amount, balance_amount, installment_amount,
        type, period, created_at, notes, status, closed_at, customer_rating
    ) VALUES (
        new_cid, 684, 'RTC', 130019, 18, '2024-12-17', '2025-06-10',
        18750.00, 18750.00, 0.0, 750.00,
        'W', 25, '2026-06-09 10:12:29', 'Auto-recreated from orphan payment records', 'closed', '2025-06-10', 100.0
    );

    UPDATE payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 684;

    UPDATE closed_cust_payment 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 684;

    UPDATE historic_payment_data 
    SET cid = new_cid
    WHERE vid = 130019 AND ano = 684;
END $$;

COMMIT;
