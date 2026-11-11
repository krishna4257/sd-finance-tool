"""
services/cashbag_engine.py
──────────────────────────
Single Source of Truth (SSOT) Cashbag Calculation Engine for Smart Counting.
Shared identically between the Web Command Portal (/cashbag) and Flutter Mobile App (/api/mobile/cashbag).
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def resolve_employee_cashbags(cur, eid: int, is_admin: bool = False) -> List[Dict[str, Any]]:
    """
    Discovers all available cashbag / village group contexts for an employee.
    If the user is an admin/superadmin, includes all active route banks / village groups so they can inspect any group.
    """
    cashbags_list = []
    seen_keys = set()

    # 1. Fetch from village_groups (Route Banks)
    if is_admin:
        cur.execute("""
            SELECT vg.id, vg.group_code, vg.group_name, vg.emp1_id, e1.name, vg.emp2_id, e2.name, vg.assigned_village_codes
            FROM village_groups vg
            LEFT JOIN employee e1 ON vg.emp1_id = e1.eid
            LEFT JOIN employee e2 ON vg.emp2_id = e2.eid
            WHERE vg.status != 'archived' OR vg.status IS NULL
            ORDER BY (CASE WHEN (vg.emp1_id = %s OR vg.emp2_id = %s) THEN 0 ELSE 1 END), vg.created_at ASC
        """, (eid, eid))
    else:
        cur.execute("""
            SELECT vg.id, vg.group_code, vg.group_name, vg.emp1_id, e1.name, vg.emp2_id, e2.name, vg.assigned_village_codes
            FROM village_groups vg
            LEFT JOIN employee e1 ON vg.emp1_id = e1.eid
            LEFT JOIN employee e2 ON vg.emp2_id = e2.eid
            WHERE (vg.emp1_id = %s OR vg.emp2_id = %s)
              AND (vg.status != 'archived' OR vg.status IS NULL)
            ORDER BY vg.created_at ASC
        """, (eid, eid))

    for r in cur.fetchall():
        gid, gcode, gname, e1, e1_name, e2, e2_name, vcodes = r
        key = f"bank_{gid}"
        if key not in seen_keys:
            seen_keys.add(key)
            cashbags_list.append({
                "id": str(gid),
                "type": "village_group",
                "bank_id": str(gid),
                "cashbag_id": None,
                "group_code": gcode or "",
                "name": gname or f"Route Bank ({gcode})",
                "emp1": e1,
                "emp1_name": e1_name or (f"Employee {e1}" if e1 else None),
                "emp2": e2,
                "emp2_name": e2_name or (f"Employee {e2}" if e2 else None),
                "village_codes": list(vcodes) if vcodes else []
            })

    # 2. Fetch from village_cashbags (Multi-cashbags / sub-routes)
    if is_admin:
        cur.execute("""
            SELECT vc.id, vc.name, vc.emp1, e1.name, vc.emp2, e2.name, vc.village_codes
            FROM village_cashbags vc
            LEFT JOIN employee e1 ON vc.emp1 = e1.eid
            LEFT JOIN employee e2 ON vc.emp2 = e2.eid
            ORDER BY (CASE WHEN (vc.emp1 = %s OR vc.emp2 = %s) THEN 0 ELSE 1 END), vc.name ASC
        """, (eid, eid))
    else:
        cur.execute("""
            SELECT vc.id, vc.name, vc.emp1, e1.name, vc.emp2, e2.name, vc.village_codes
            FROM village_cashbags vc
            LEFT JOIN employee e1 ON vc.emp1 = e1.eid
            LEFT JOIN employee e2 ON vc.emp2 = e2.eid
            WHERE vc.emp1 = %s OR vc.emp2 = %s
            ORDER BY vc.name ASC
        """, (eid, eid))
    for r in cur.fetchall():
        cid, cname, e1, e1_name, e2, e2_name, vcodes = r
        key = f"cb_{cid}"
        # If this cashbag matches an existing bank for the same pair and same village codes, link them
        matched_bank = next((b for b in cashbags_list if b.get("bank_id") and b.get("emp1") == e1 and b.get("emp2") == e2 and set(b.get("village_codes", [])) == set(vcodes or [])), None)
        if matched_bank:
            matched_bank["cashbag_id"] = str(cid)
            continue

        if key not in seen_keys:
            seen_keys.add(key)
            cashbags_list.append({
                "id": str(cid),
                "type": "village_cashbag",
                "bank_id": None,
                "cashbag_id": str(cid),
                "group_code": "",
                "name": cname or "Main Cashbag",
                "emp1": e1,
                "emp1_name": e1_name or (f"Employee {e1}" if e1 else None),
                "emp2": e2,
                "emp2_name": e2_name or (f"Employee {e2}" if e2 else None),
                "village_codes": list(vcodes) if vcodes else []
            })

    # 3. Fallback: Distinct active employee pairs in village table
    if not cashbags_list:
        cur.execute("""
            SELECT DISTINCT v.emp1, e1.name, v.emp2, e2.name
            FROM village v
            LEFT JOIN employee e1 ON v.emp1 = e1.eid
            LEFT JOIN employee e2 ON v.emp2 = e2.eid
            WHERE (v.emp1 = %s OR v.emp2 = %s) AND v.status = 'active'
        """, (eid, eid))
        for r in cur.fetchall():
            e1, e1_name, e2, e2_name = r
            key = f"pair_{e1}_{e2}"
            if key not in seen_keys:
                seen_keys.add(key)
                pair_name = f"{e1_name or e1} + {e2_name or e2}" if e2 else (e1_name or f"Employee {e1}")
                cashbags_list.append({
                    "id": key,
                    "type": "village_pair",
                    "bank_id": None,
                    "cashbag_id": None,
                    "group_code": "",
                    "name": pair_name,
                    "emp1": e1,
                    "emp1_name": e1_name,
                    "emp2": e2,
                    "emp2_name": e2_name,
                    "village_codes": []
                })

    return cashbags_list


def compute_cashbag_metrics(
    cur,
    emp1: int,
    emp2: Optional[int] = None,
    bank_id: Optional[str] = None,
    cashbag_id: Optional[str] = None,
    limit_val: int = 250
) -> Dict[str, Any]:
    """
    Computes the complete, authoritative cashbag financial metrics and unified ledger.
    Matches the exact mathematical formula and SQL definitions of the Web Cashbag Management screen.
    """
    # 1. Resolve current_bank from village_groups
    current_bank = None
    if bank_id:
        cur.execute("""
            SELECT id, group_code, group_name, emp1_id, emp2_id, assigned_village_codes
            FROM village_groups
            WHERE id = %s
        """, (bank_id,))
        brow = cur.fetchone()
        if brow:
            current_bank = {
                "id": str(brow[0]),
                "group_code": brow[1],
                "group_name": brow[2],
                "emp1_id": brow[3],
                "emp2_id": brow[4],
                "assigned_village_codes": list(brow[5]) if brow[5] else []
            }
            if not emp1 and brow[3]:
                emp1 = brow[3]
            if not emp2 and brow[4]:
                emp2 = brow[4]

    if not current_bank and emp1:
        if emp2:
            cur.execute("""
                SELECT id, group_code, group_name, emp1_id, emp2_id, assigned_village_codes
                FROM village_groups
                WHERE (emp1_id = %s AND emp2_id = %s) OR (emp1_id = %s AND emp2_id = %s)
                ORDER BY created_at DESC LIMIT 1
            """, (emp1, emp2, emp2, emp1))
        else:
            cur.execute("""
                SELECT id, group_code, group_name, emp1_id, emp2_id, assigned_village_codes
                FROM village_groups
                WHERE emp1_id = %s AND (emp2_id IS NULL OR emp2_id = %s)
                ORDER BY created_at DESC LIMIT 1
            """, (emp1, emp1))
        brow = cur.fetchone()
        if brow:
            current_bank = {
                "id": str(brow[0]),
                "group_code": brow[1],
                "group_name": brow[2],
                "emp1_id": brow[3],
                "emp2_id": brow[4],
                "assigned_village_codes": list(brow[5]) if brow[5] else []
            }

    # 2. Fetch group_banks
    if emp2:
        cur.execute("""
            SELECT id, group_code, group_name
            FROM village_groups
            WHERE (emp1_id = %s AND emp2_id = %s) OR (emp1_id = %s AND emp2_id = %s)
            ORDER BY group_name
        """, (emp1, emp2, emp2, emp1))
    else:
        cur.execute("""
            SELECT id, group_code, group_name
            FROM village_groups
            WHERE emp1_id = %s AND (emp2_id IS NULL OR emp2_id = %s)
            ORDER BY group_name
        """, (emp1, emp1))
    group_banks = [{"id": str(r[0]), "group_code": r[1], "group_name": r[2]} for r in cur.fetchall()]

    # 3. Fetch group_cashbags
    if emp2:
        cur.execute("""
            SELECT id, name, village_codes
            FROM village_cashbags
            WHERE emp1 = %s AND emp2 = %s
            ORDER BY name
        """, (emp1, emp2))
    else:
        cur.execute("""
            SELECT id, name, village_codes
            FROM village_cashbags
            WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = %s)
            ORDER BY name
        """, (emp1, emp1))
    group_cashbags = [{
        "id": str(r[0]),
        "name": r[1],
        "village_codes": list(r[2]) if r[2] else []
    } for r in cur.fetchall()]

    # Resolve active cashbag if cashbag_id supplied
    current_cashbag = None
    scoped_village_codes = None
    if cashbag_id:
        for cb in group_cashbags:
            if cb["id"] == str(cashbag_id):
                current_cashbag = cb
                scoped_village_codes = cb["village_codes"]
                break

    # Build emp pair WHERE clause helper
    if emp2:
        pair_filter = "emp1 = %s AND emp2 = %s"
        pair_params_single = (emp1, emp2)
    else:
        pair_filter = "emp1 = %s AND (emp2 IS NULL OR emp2 = emp1)"
        pair_params_single = (emp1,)

    # Fetch Employee Names
    emp1_name = f"Employee {emp1}"
    if emp1:
        cur.execute("SELECT name FROM employee WHERE eid = %s", (emp1,))
        row_e1 = cur.fetchone()
        if row_e1:
            emp1_name = row_e1[0]

    emp2_name = None
    if emp2:
        cur.execute("SELECT name FROM employee WHERE eid = %s", (emp2,))
        row_e2 = cur.fetchone()
        if row_e2:
            emp2_name = row_e2[0]

    # Resolve Villages
    if scoped_village_codes:
        cur.execute("""
            SELECT vid, village_name, village_code
            FROM village
            WHERE village_code = ANY(%s) AND status = 'active'
            ORDER BY village_code
        """, (scoped_village_codes,))
    elif emp2:
        cur.execute("""
            SELECT vid, village_name, village_code
            FROM village
            WHERE emp1 = %s AND emp2 = %s AND status = 'active'
            ORDER BY village_code
        """, (emp1, emp2))
    else:
        cur.execute("""
            SELECT vid, village_name, village_code
            FROM village
            WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = emp1) AND status = 'active'
            ORDER BY village_code
        """, (emp1,))
    rows_v = cur.fetchall()
    group_villages = [{"id": r[0], "name": r[1], "code": r[2]} for r in rows_v]
    vids = [r[0] for r in rows_v]

    # 4. Manual Transactions Sum
    cur.execute(f"""
        SELECT 
            COALESCE(SUM(CASE WHEN txn = 'OFFICE_CASH' THEN amount ELSE 0 END), 0) AS office_cash,
            COALESCE(SUM(CASE WHEN txn = 'OFFICE_CASH' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS office_cash_cash,
            COALESCE(SUM(CASE WHEN txn = 'OFFICE_CASH' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS office_cash_upi,
            
            COALESCE(SUM(CASE WHEN txn = 'EXPENSE' THEN amount ELSE 0 END), 0) AS expenses,
            COALESCE(SUM(CASE WHEN txn = 'EXPENSE' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS expenses_cash,
            COALESCE(SUM(CASE WHEN txn = 'EXPENSE' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS expenses_upi,
            
            COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'ADD' THEN amount ELSE 0 END), 0) AS adj_add,
            COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'ADD' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS adj_add_cash,
            COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'ADD' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS adj_add_upi,
            
            COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'MINUS' THEN amount ELSE 0 END), 0) AS adj_minus,
            COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'MINUS' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS adj_minus_cash,
            COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'MINUS' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS adj_minus_upi,

            COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'PROFIT' THEN amount ELSE 0 END), 0) AS profit_val,
            COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'PROFIT' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS profit_cash,
            COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'PROFIT' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS profit_upi,
            
            COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'LOSS' THEN amount ELSE 0 END), 0) AS loss_val,
            COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'LOSS' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS loss_cash,
            COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'LOSS' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS loss_upi
        FROM cashbag_transactions
        WHERE {pair_filter}
    """, pair_params_single)
    row_manual = cur.fetchone()
    office_cash = float(row_manual[0] or 0)
    office_cash_cash = float(row_manual[1] or 0)
    office_cash_upi = float(row_manual[2] or 0)
    expenses = float(row_manual[3] or 0)
    expenses_cash = float(row_manual[4] or 0)
    expenses_upi = float(row_manual[5] or 0)
    adjustments_add = float(row_manual[6] or 0)
    adjustments_add_cash = float(row_manual[7] or 0)
    adjustments_add_upi = float(row_manual[8] or 0)
    adjustments_minus = float(row_manual[9] or 0)
    adjustments_minus_cash = float(row_manual[10] or 0)
    adjustments_minus_upi = float(row_manual[11] or 0)
    profit_val = float(row_manual[12] or 0)
    profit_cash = float(row_manual[13] or 0)
    profit_upi = float(row_manual[14] or 0)
    loss_val = float(row_manual[15] or 0)
    loss_cash = float(row_manual[16] or 0)
    loss_upi = float(row_manual[17] or 0)
    profit_loss_net = profit_val - loss_val

    # 5. Installments Sum (from v_all_payments)
    installments = 0.0
    installments_cash = 0.0
    installments_upi = 0.0
    if vids:
        cur.execute("""
            SELECT 
                COALESCE(SUM(p.amt), 0) AS total,
                COALESCE(SUM(CASE 
                    WHEN LOWER(p.payment_type) = 'cash' THEN p.amt 
                    WHEN LOWER(p.payment_type) = 'upi' THEN 0 
                    WHEN LOWER(p.payment_type) = 'partial' THEN COALESCE(p.cash_amount, 0)
                    ELSE p.amt 
                END), 0) AS cash,
                COALESCE(SUM(CASE 
                    WHEN LOWER(p.payment_type) = 'upi' THEN p.amt 
                    WHEN LOWER(p.payment_type) = 'partial' THEN COALESCE(p.upi_amount, 0)
                    ELSE 0 
                END), 0) AS upi
            FROM v_all_payments p
            WHERE p.vid = ANY(%s)
        """, (vids,))
        row_inst = cur.fetchone()
        installments = float(row_inst[0] or 0)
        installments_cash = float(row_inst[1] or 0)
        installments_upi = float(row_inst[2] or 0)

    # 6. Loans & Commissions Sum (from v_all_customers)
    loans_disbursed = 0.0
    loans_disbursed_cash = 0.0
    loans_disbursed_upi = 0.0
    loan_commission = 0.0
    loan_commission_cash = 0.0
    loan_commission_upi = 0.0
    interest_total = 0.0
    base_amount_total = 0.0
    outstanding_balance_total = 0.0
    active_balance_total = 0.0
    if vids:
        cur.execute("""
            SELECT 
                COALESCE(SUM(c.total_amount), 0) AS loans_disbursed,
                COALESCE(SUM(CASE 
                    WHEN LOWER(c.payment_type) = 'upi' THEN 0
                    ELSE c.total_amount
                END), 0) AS loans_disbursed_cash,
                COALESCE(SUM(CASE 
                    WHEN LOWER(c.payment_type) = 'upi' THEN c.total_amount
                    ELSE 0
                END), 0) AS loans_disbursed_upi,
                
                COALESCE(SUM(CASE 
                    WHEN c.cutting_amount > 0 THEN c.cutting_amount 
                    ELSE ROUND(c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0), 2) 
                END), 0) AS loan_commission,
                COALESCE(SUM(CASE 
                    WHEN LOWER(c.payment_type) = 'upi' THEN 0
                    ELSE (CASE WHEN c.cutting_amount > 0 THEN c.cutting_amount ELSE ROUND(c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0), 2) END)
                END), 0) AS loan_commission_cash,
                COALESCE(SUM(CASE 
                    WHEN LOWER(c.payment_type) = 'upi' THEN (CASE WHEN c.cutting_amount > 0 THEN c.cutting_amount ELSE ROUND(c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0), 2) END)
                    ELSE 0
                END), 0) AS loan_commission_upi,
                
                COALESCE(SUM(CASE 
                    WHEN c.interest_amount > 0 THEN c.interest_amount 
                    ELSE ROUND(c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0), 2) 
                END), 0) AS interest_total,

                COALESCE(SUM(CASE 
                    WHEN c.base_amount > 0 THEN c.base_amount 
                    ELSE ROUND(c.total_amount - (c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0)) - (c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0)), 2) 
                END), 0) AS base_amount_total,

                COALESCE(SUM(c.balance_amount), 0) AS outstanding_balance_total,
                COALESCE(SUM(CASE WHEN c.status = 'active' THEN c.balance_amount ELSE 0 END), 0) AS active_balance_total
            FROM v_all_customers c
            JOIN village v ON c.vid = v.vid
            WHERE c.vid = ANY(%s) AND c.status != 'deleted'
        """, (vids,))
        row_loans = cur.fetchone()
        loans_disbursed = float(row_loans[0] or 0)
        loans_disbursed_cash = float(row_loans[1] or 0)
        loans_disbursed_upi = float(row_loans[2] or 0)
        loan_commission = float(row_loans[3] or 0)
        loan_commission_cash = float(row_loans[4] or 0)
        loan_commission_upi = float(row_loans[5] or 0)
        interest_total = float(row_loans[6] or 0)
        base_amount_total = float(row_loans[7] or 0)
        outstanding_balance_total = float(row_loans[8] or 0)
        active_balance_total = float(row_loans[9] or 0)

    # 7. Capital Deployed & Withdrawn
    active_bank_id = current_bank["id"] if current_bank else bank_id
    cb_group_filter = f"({pair_filter} OR group_id = %s)" if active_bank_id else pair_filter
    cb_group_params = pair_params_single + (active_bank_id,) if active_bank_id else pair_params_single
    cur.execute(f"""
        SELECT 
            COALESCE(SUM(CASE WHEN txn IN ('CAPITAL_DEPLOYED', 'OFFICE_CASH') AND (notes ILIKE 'Capital Deployed%%' OR txn = 'CAPITAL_DEPLOYED') THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN txn IN ('CAPITAL_WITHDRAWN', 'WITHDRAWN', 'INTEREST_WITHDRAWN') OR notes ILIKE '%%Withdrawal%%' THEN amount ELSE 0 END), 0)
        FROM cashbag_transactions
        WHERE {cb_group_filter}
    """, cb_group_params)
    row_caps = cur.fetchone()
    capital_deployed = float(row_caps[0] or 0)
    total_withdrawn = float(row_caps[1] or 0)

    if current_bank:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM group_capital_allocations
            WHERE group_id = %s AND (is_reversed IS FALSE OR is_reversed IS NULL)
        """, (current_bank["id"],))
        cap_gca = float(cur.fetchone()[0] or 0)
        if cap_gca > capital_deployed:
            capital_deployed = cap_gca

        cur.execute("""
            SELECT COALESCE(SUM(total_withdrawn), 0)
            FROM group_withdrawal_logs
            WHERE group_id = %s AND (is_reversed IS FALSE OR is_reversed IS NULL)
        """, (current_bank["id"],))
        wdr_gwl = float(cur.fetchone()[0] or 0)
        if wdr_gwl > total_withdrawn:
            total_withdrawn = wdr_gwl

    # 8. Interest Discount Total
    interest_discount_total = 0.0
    if vids:
        cur.execute("""
            SELECT COALESCE(SUM(interest_discount), 0)
            FROM v_all_customers
            WHERE vid = ANY(%s) AND status != 'deleted'
        """, (vids,))
        row_disc = cur.fetchone()
        interest_discount_total = float(row_disc[0] or 0) if row_disc else 0.0

    # 9. Final Cashbag Totals (The Canonical Formula)
    cashbag_total_cash = (
        capital_deployed
        + office_cash_cash
        + installments_cash
        + loan_commission_cash
        + interest_total
        + adjustments_add_cash
        + profit_cash
        - loans_disbursed_cash
        - expenses_cash
        - adjustments_minus_cash
        - loss_cash
        - total_withdrawn
    )
    cashbag_total_upi = (
        office_cash_upi
        + installments_upi
        + loan_commission_upi
        + adjustments_add_upi
        + profit_upi
        - loans_disbursed_upi
        - expenses_upi
        - adjustments_minus_upi
        - loss_upi
    )
    cashbag_total = cashbag_total_cash + cashbag_total_upi

    # 10. Unified Transaction History (Ledger)
    transactions = []
    if vids:
        query = f"""
            SELECT 
                id,
                txn,
                txn_sub,
                txn_type,
                amount,
                notes,
                created_by,
                TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'DD/MM/YYYY HH12:MI AM') AS created_at
            FROM (
                -- Manual entries
                SELECT 
                    id::text AS id,
                    txn,
                    txn_sub,
                    txn_type,
                    amount,
                    notes,
                    created_by,
                    created_at
                FROM cashbag_transactions
                WHERE {cb_group_filter}
                  AND (txn IN ('OFFICE_CASH', 'EXPENSE', 'ADJUSTMENT', 'PROFIT_LOSS', 'CAPITAL_DEPLOYED', 'CAPITAL_WITHDRAWN', 'WITHDRAWN', 'INTEREST_WITHDRAWN') 
                       OR notes ILIKE '%%Withdrawal%%' 
                       OR notes ILIKE 'Capital Deployed%%')

                UNION ALL

                -- Customer Loans (Auto)
                SELECT 
                    'loan_' || c.cid::text AS id,
                    'LOAN' AS txn,
                    NULL AS txn_sub,
                    COALESCE(c.payment_type, 'CASH') AS txn_type,
                    CASE 
                        WHEN c.base_amount > 0 THEN c.base_amount
                        ELSE ROUND(c.total_amount - (c.total_amount * (v.interest_rate / 100.0)) - (c.total_amount * (v.cutting_rate / 100.0)), 2)
                    END AS amount,
                    'Loan issued to ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                    'System' AS created_by,
                    c.start_date::timestamp WITH time zone AS created_at
                FROM (
                    SELECT cid, base_amount, total_amount, cutting_amount, name, ano, start_date, status, vid, payment_type FROM customer
                    UNION ALL
                    SELECT cid, base_amount, total_amount, cutting_amount, name, ano, start_date, status, vid, payment_type FROM closed_cust_account
                ) c
                JOIN village v ON c.vid = v.vid
                WHERE c.vid = ANY(%s) AND c.status != 'deleted'

                UNION ALL

                -- Customer Loan Commission / Rusum (Auto)
                SELECT 
                    'comm_' || c.cid::text AS id,
                    'LOAN_COMMISION' AS txn,
                    NULL AS txn_sub,
                    COALESCE(c.payment_type, 'CASH') AS txn_type,
                    CASE 
                        WHEN c.cutting_amount > 0 THEN c.cutting_amount
                        ELSE ROUND(c.total_amount * (v.cutting_rate / 100.0), 2)
                    END AS amount,
                    'Rusum - ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                    'System' AS created_by,
                    c.start_date::timestamp WITH time zone AS created_at
                FROM (
                    SELECT cid, base_amount, total_amount, cutting_amount, name, ano, start_date, status, vid, payment_type FROM customer
                    UNION ALL
                    SELECT cid, base_amount, total_amount, cutting_amount, name, ano, start_date, status, vid, payment_type FROM closed_cust_account
                ) c
                JOIN village v ON c.vid = v.vid
                WHERE c.vid = ANY(%s) AND c.status != 'deleted'

                UNION ALL

                -- Customer Payments (Auto)
                SELECT 
                    'pay_' || p.pid::text AS id,
                    'INSTALLMENT_AMOUNT' AS txn,
                    NULL AS txn_sub,
                    COALESCE(p.payment_type, 'CASH') AS txn_type,
                    p.amt AS amount,
                    'Collection from ' || c.name || ' (A/c: ' || c.ano || ')' AS notes,
                    'System' AS created_by,
                    p.created_at AS created_at
                FROM v_all_payments p
                JOIN v_all_customers c ON p.cid = c.cid
                WHERE p.vid = ANY(%s)
            ) AS combined
            ORDER BY combined.created_at DESC, id DESC
            LIMIT %s
        """
        params = cb_group_params + (vids, vids, vids, limit_val)
        cur.execute(query, params)
    else:
        query = f"""
            SELECT 
                id::text AS id,
                txn,
                txn_sub,
                txn_type,
                amount,
                notes,
                created_by,
                TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'DD/MM/YYYY HH12:MI AM') AS created_at
            FROM cashbag_transactions
            WHERE {cb_group_filter}
              AND (txn IN ('OFFICE_CASH', 'EXPENSE', 'ADJUSTMENT', 'PROFIT_LOSS', 'CAPITAL_DEPLOYED', 'CAPITAL_WITHDRAWN', 'WITHDRAWN', 'INTEREST_WITHDRAWN') 
                   OR notes ILIKE '%%Withdrawal%%' 
                   OR notes ILIKE 'Capital Deployed%%')
            ORDER BY created_at DESC, id DESC
            LIMIT %s
        """
        cur.execute(query, cb_group_params + (limit_val,))

    rows = cur.fetchall()
    for row in rows:
        amt = float(row[4] or 0)
        ttype = str(row[3] or 'CASH').upper()
        cash_part = amt if ttype == 'CASH' else 0.0
        upi_part = amt if ttype == 'UPI' else 0.0
        transactions.append({
            "id":         row[0],
            "txn":        row[1],
            "txn_sub":    row[2],
            "txn_type":   ttype,
            "amount":     amt,
            "cash_amount": cash_part,
            "upi_amount":  upi_part,
            "notes":      row[5],
            "created_by": row[6],
            "created_at": row[7]
        })

    return {
        "emp1": emp1,
        "emp2": emp2,
        "emp1_name": emp1_name,
        "emp2_name": emp2_name,
        "group_villages": group_villages,
        "current_bank": current_bank,
        "current_cashbag": current_cashbag,
        "group_banks": group_banks,
        "group_cashbags": group_cashbags,
        "cashbag_total": cashbag_total,
        "cashbag_total_cash": cashbag_total_cash,
        "cashbag_total_upi": cashbag_total_upi,
        "capital_deployed": capital_deployed,
        "total_withdrawn": total_withdrawn,
        "capital_withdrawn": total_withdrawn,
        "installments": installments,
        "installments_cash": installments_cash,
        "installments_upi": installments_upi,
        "loans_disbursed": loans_disbursed,
        "loans_disbursed_cash": loans_disbursed_cash,
        "loans_disbursed_upi": loans_disbursed_upi,
        "loan_commission": loan_commission,
        "loan_commission_cash": loan_commission_cash,
        "loan_commission_upi": loan_commission_upi,
        "interest_total": interest_total,
        "interest_discount_total": interest_discount_total,
        "expenses": expenses,
        "expenses_cash": expenses_cash,
        "expenses_upi": expenses_upi,
        "adjustments_add": adjustments_add,
        "adjustments_add_cash": adjustments_add_cash,
        "adjustments_add_upi": adjustments_add_upi,
        "adjustments_minus": adjustments_minus,
        "adjustments_minus_cash": adjustments_minus_cash,
        "adjustments_minus_upi": adjustments_minus_upi,
        "profit_val": profit_val,
        "loss_val": loss_val,
        "profit_loss_net": profit_loss_net,
        "office_cash": office_cash,
        "office_cash_cash": office_cash_cash,
        "office_cash_upi": office_cash_upi,
        "base_amount_total": base_amount_total,
        "outstanding_balance_total": outstanding_balance_total,
        "active_balance_total": active_balance_total,
        "transactions": transactions,
        "limit_val": limit_val
    }
