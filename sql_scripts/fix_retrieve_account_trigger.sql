-- Fix fn_trg_customer_auto_ucid_link to prevent duplicate customer_loan_link / customer_master
-- when retrieving/restoring an account from closed_cust_account back into customer.

CREATE OR REPLACE FUNCTION public.fn_trg_customer_auto_ucid_link()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
        v_ucid BIGINT;
        v_cycle_no INT;
        v_parent_ano INT;
    BEGIN
        IF TG_OP = 'INSERT' THEN
            -- Check if this cid already exists in customer_loan_link (e.g. account retrieved from closed_cust_account or re-inserted)
            IF EXISTS (SELECT 1 FROM customer_loan_link WHERE cid = NEW.cid) THEN
                UPDATE customer_loan_link
                SET record_tier = 'active',
                    status = COALESCE(NEW.status, 'open'),
                    vid = NEW.vid,
                    ano = NEW.ano,
                    pano = NEW.pano,
                    start_date = NEW.start_date,
                    end_date = NEW.end_date,
                    total_amount = NEW.total_amount,
                    paid_amount = NEW.paid_amount,
                    balance_amount = NEW.balance_amount
                WHERE cid = NEW.cid;

                -- Update customer_master active balance
                UPDATE customer_master cm
                SET current_active_balance = (
                        SELECT COALESCE(SUM(cll.balance_amount), 0)
                        FROM customer_loan_link cll
                        WHERE cll.ucid = cm.ucid AND cll.record_tier = 'active'
                    ),
                    updated_at = NOW()
                FROM customer_loan_link cll_target
                WHERE cll_target.cid = NEW.cid 
                  AND cm.ucid = cll_target.ucid;

                RETURN NEW;
            END IF;

            -- 1. Try PANO lineage in same village
            IF NEW.pano IS NOT NULL AND NEW.pano ~ '^[0-9]+$' AND NEW.pano::integer > 0 THEN
                v_parent_ano := NEW.pano::integer;
                SELECT ucid, cycle_number + 1 INTO v_ucid, v_cycle_no
                FROM customer_loan_link
                WHERE vid = NEW.vid AND ano = v_parent_ano
                ORDER BY cycle_number DESC
                LIMIT 1;
            END IF;

            -- 2. Try Aadhaar match if not matched
            IF v_ucid IS NULL AND NEW.aadhaar_number IS NOT NULL AND length(trim(NEW.aadhaar_number)) = 12 THEN
                SELECT ucid INTO v_ucid
                FROM customer_master
                WHERE aadhaar_number = trim(NEW.aadhaar_number)
                LIMIT 1;
                
                IF v_ucid IS NOT NULL THEN
                    SELECT COALESCE(MAX(cycle_number), 0) + 1 INTO v_cycle_no
                    FROM customer_loan_link
                    WHERE ucid = v_ucid;
                END IF;
            END IF;

            -- 3. Brand new borrower: Create customer_master entry
            IF v_ucid IS NULL THEN
                INSERT INTO customer_master (
                    primary_name,
                    primary_vid,
                    phone_number,
                    aadhaar_number,
                    total_loan_cycles,
                    first_loan_date,
                    latest_loan_date,
                    lifetime_borrowed,
                    lifetime_repaid,
                    current_active_balance,
                    customer_risk_tier
                ) VALUES (
                    UPPER(TRIM(NEW.name)),
                    NEW.vid,
                    NEW.phone_number,
                    NEW.aadhaar_number,
                    1,
                    NEW.start_date,
                    NEW.start_date,
                    COALESCE(NEW.total_amount, 0),
                    COALESCE(NEW.paid_amount, 0),
                    COALESCE(NEW.balance_amount, 0),
                    'standard'
                ) RETURNING ucid INTO v_ucid;
                v_cycle_no := 1;
            ELSE
                -- Update existing customer_master aggregates
                UPDATE customer_master
                SET total_loan_cycles = GREATEST(total_loan_cycles, v_cycle_no),
                    latest_loan_date = GREATEST(latest_loan_date, NEW.start_date),
                    lifetime_borrowed = lifetime_borrowed + COALESCE(NEW.total_amount, 0),
                    lifetime_repaid = lifetime_repaid + COALESCE(NEW.paid_amount, 0),
                    current_active_balance = current_active_balance + COALESCE(NEW.balance_amount, 0),
                    phone_number = COALESCE(phone_number, NEW.phone_number),
                    aadhaar_number = COALESCE(aadhaar_number, NEW.aadhaar_number),
                    updated_at = NOW()
                WHERE ucid = v_ucid;
            END IF;

            -- 4. Insert into customer_loan_link
            INSERT INTO customer_loan_link (
                ucid,
                cid,
                vid,
                ano,
                pano,
                record_tier,
                cycle_number,
                start_date,
                end_date,
                total_amount,
                paid_amount,
                balance_amount,
                status,
                created_at
            ) VALUES (
                v_ucid,
                NEW.cid,
                NEW.vid,
                NEW.ano,
                NEW.pano,
                'active',
                v_cycle_no,
                NEW.start_date,
                NEW.end_date,
                NEW.total_amount,
                NEW.paid_amount,
                NEW.balance_amount,
                NEW.status,
                COALESCE(NEW.created_at, NOW())
            ) ON CONFLICT (cid, record_tier) DO UPDATE
            SET ucid = EXCLUDED.ucid,
                cycle_number = EXCLUDED.cycle_number,
                total_amount = EXCLUDED.total_amount,
                paid_amount = EXCLUDED.paid_amount,
                balance_amount = EXCLUDED.balance_amount,
                status = EXCLUDED.status;

        ELSIF TG_OP = 'UPDATE' THEN
            -- Propagate modified loan amounts, dates, and status to customer_loan_link
            UPDATE customer_loan_link
            SET total_amount = NEW.total_amount,
                paid_amount = NEW.paid_amount,
                balance_amount = NEW.balance_amount,
                start_date = NEW.start_date,
                end_date = NEW.end_date,
                status = NEW.status
            WHERE cid = NEW.cid AND record_tier = 'active';

            -- Refresh customer_master totals if total_amount or balance_amount was adjusted
            IF (NEW.total_amount IS DISTINCT FROM OLD.total_amount) 
               OR (NEW.balance_amount IS DISTINCT FROM OLD.balance_amount) THEN
                UPDATE customer_master cm
                SET lifetime_borrowed = (
                        SELECT COALESCE(SUM(cll.total_amount), 0)
                        FROM customer_loan_link cll
                        WHERE cll.ucid = cm.ucid
                    ),
                    current_active_balance = (
                        SELECT COALESCE(SUM(cll.balance_amount), 0)
                        FROM customer_loan_link cll
                        WHERE cll.ucid = cm.ucid AND cll.record_tier = 'active'
                    ),
                    updated_at = NOW()
                FROM customer_loan_link cll_target
                WHERE cll_target.cid = NEW.cid 
                  AND cll_target.record_tier = 'active' 
                  AND cm.ucid = cll_target.ucid;
            END IF;
        END IF;

        RETURN NEW;
    END;
$function$;
