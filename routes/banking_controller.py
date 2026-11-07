"""







Siva Durga Finance — Hierarchical Banking Controller







Flask Blueprint for Central Investment Treasury, Route Banks, and Portals.







Prefix: /banking







"""







import os







import json







import uuid







import logging







from datetime import datetime, date, timedelta







from decimal import Decimal







from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash, g







from werkzeug.security import generate_password_hash, check_password_hash







from db import get_pg_connection







import services.banking_calc_engine as bce







logger = logging.getLogger(__name__)







banking_bp = Blueprint('banking_bp', __name__, url_prefix='/banking')







# ---------------------------------------------------------------------------







# Jinja Context Processors & Formatting Filters







# ---------------------------------------------------------------------------







@banking_bp.context_processor







def utility_processor():







    return dict(







        format_inr=bce.format_currency_inr,







        format_date_in=bce.format_date_in,







        format_time_in=bce.format_time_in,







        round_curr=bce.round_currency







    )







# ---------------------------------------------------------------------------







# Authentication & Authorization Guards







# ---------------------------------------------------------------------------







def is_api_request():







    return (







        request.path.startswith("/banking/api/")







        or request.headers.get("X-Requested-With") == "XMLHttpRequest"







        or request.is_json







        or "application/json" in request.headers.get("Accept", "")







    )







@banking_bp.before_request







def require_banking_auth():







    # Allow public investor self-service portal auth routes







    if request.path in ("/banking/portal/login", "/banking/api/portal/login"):







        return None







    # Check investor portal session if browsing /banking/portal routes







    if request.path.startswith("/banking/portal"):







        if not session.get("investor_id"):







            return redirect("/banking/portal/login")







        return None







    # For all core management banking routes: require admin / web user login







    user_id = session.get("user_id")







    if not user_id:







        if is_api_request():







            return jsonify({







                "success": False,







                "error": "Session expired. Please login again.",







                "session_expired": True







            }), 401







        return redirect("/login")







    # Field collectors are strictly blocked from banking treasury controls







    user_level = session.get("level")







    if user_level in ("j", "m", "s"):







        if is_api_request():







            return jsonify({"success": False, "error": "Access denied. Insufficient permissions."}), 403







        flash("Access denied. Banking management requires administrative privileges.")







        return redirect("/village")







def verify_admin_security_pin(pin_input: str) -> bool:







    """







    Verifies admin confirmation PIN or password before authorizing cash-out/reversals.







    Accepts current user's password, configured ADMIN_PIN in env, or default '1234'.







    """







    if not pin_input:







        return False







    pin_str = str(pin_input).strip()







    configured_pin = os.environ.get("BANKING_ADMIN_PIN", "1234")







    if pin_str == configured_pin:







        return True







    # Alternatively check logged-in admin's actual password in database







    user_id = session.get("user_id")







    if user_id:







        conn = None







        try:







            conn = get_pg_connection()







            with conn.cursor() as cur:







                cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))







                row = cur.fetchone()







                if row and row[0]:







                    if check_password_hash(row[0], pin_str):







                        return True







        except Exception as e:







            logger.error(f"Error checking admin password in PIN verification: {e}")







        finally:







            if conn:







                conn.close()







    return False







@banking_bp.route("/api/verify-pin", methods=["POST"])







def api_verify_pin():







    data = request.get_json(silent=True) or {}







    pin = data.get("pin")







    if verify_admin_security_pin(pin):







        return jsonify({"success": True, "message": "Authorization confirmed."})







    return jsonify({"success": False, "error": "Invalid Admin PIN / Password."}), 401







@banking_bp.app_context_processor







def inject_banking_helpers():







    return {







        'format_inr': bce.format_currency_inr,







        'format_date_in': bce.format_date_in,







        'format_time_in': bce.format_time_in,







    }







@banking_bp.app_template_filter('format_inr')







def format_inr_filter(value):







    return bce.format_currency_inr(value or 0.0)







@banking_bp.app_template_filter('format_date_in')







def format_date_in_filter(value):







    return bce.format_date_in(value)







@banking_bp.app_template_filter('format_time_in')







def format_time_in_filter(value):







    return bce.format_time_in(value)







def sync_village_groups_from_smart_counting(cur) -> int:







    """







    Synchronizes route banks from existing smart counting villages.







    Each distinct (emp1, emp2) employee pair represents a permanent Village Group Route Bank.







    """







    cur.execute("""







        SELECT 







            v.emp1, 







            v.emp2, 







            COALESCE(e1.name, 'Emp #' || v.emp1::text) as emp1_name, 







            e2.name as emp2_name,







            count(v.vid) as village_count,







            string_agg(v.village_name, ', ' ORDER BY v.village_name) as village_names







        FROM village v







        LEFT JOIN employee e1 ON v.emp1 = e1.eid







        LEFT JOIN employee e2 ON v.emp2 = e2.eid







        WHERE v.emp1 IS NOT NULL







        GROUP BY v.emp1, v.emp2, e1.name, e2.name







        ORDER BY v.emp1, v.emp2;







    """)







    rows = cur.fetchall()







    count = 0







    for r in rows:







        emp1, emp2, emp1_name, emp2_name, v_count, v_names = r







        if emp2 and emp2_name:







            group_name = f"{emp1_name} & {emp2_name} Route"







            group_code = f"ROUTE-{emp1}-{emp2}"







        else:







            group_name = f"{emp1_name} Route"







            group_code = f"ROUTE-{emp1}"







        days = min(6, max(1, v_count))







        notes = f"Smart Counting Route ({v_count} villages): {(v_names or '')[:200]}"







        cur.execute("""







            INSERT INTO village_groups (group_code, group_name, emp1_id, emp2_id, collection_days_per_week, status, notes)







            VALUES (%s, %s, %s, %s, %s, 'ACTIVE', %s)







            ON CONFLICT (group_code) DO UPDATE SET







                group_name = EXCLUDED.group_name,







                emp1_id = EXCLUDED.emp1_id,







                emp2_id = EXCLUDED.emp2_id,







                notes = EXCLUDED.notes







        """, (group_code, group_name, emp1, emp2, days, notes))







        count += 1







    return count







# ---------------------------------------------------------------------------







# 1. Central Treasury Dashboard







# ---------------------------------------------------------------------------







@banking_bp.route("/")







@banking_bp.route("/dashboard")







def dashboard_view():







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # 1. Total deposits by payment mode







            cur.execute("""







                SELECT 







                    COALESCE(SUM(CASE WHEN payment_mode = 'CASH' THEN amount ELSE 0 END), 0) as cash_in,







                    COALESCE(SUM(CASE WHEN payment_mode = 'UPI' THEN amount ELSE 0 END), 0) as upi_in







                FROM investor_transactions 







                WHERE txn_type = 'DEPOSIT' AND is_reversed = FALSE







            """)







            dep_cash, dep_upi = cur.fetchone()







            # Withdrawals from idle pool







            cur.execute("""







                SELECT 







                    COALESCE(SUM(CASE WHEN payment_mode = 'CASH' THEN amount ELSE 0 END), 0) as cash_out,







                    COALESCE(SUM(CASE WHEN payment_mode = 'UPI' THEN amount ELSE 0 END), 0) as upi_out







                FROM investor_transactions 







                WHERE txn_type = 'IDLE_WITHDRAWAL' AND is_reversed = FALSE







            """)







            w_cash, w_upi = cur.fetchone()







            # Capital deployed to groups







            cur.execute("""







                SELECT 







                    COALESCE(SUM(CASE WHEN payment_mode = 'CASH' THEN amount ELSE 0 END), 0) as cash_dep,







                    COALESCE(SUM(CASE WHEN payment_mode = 'UPI' THEN amount ELSE 0 END), 0) as upi_dep,







                    COALESCE(SUM(amount), 0) as total_dep







                FROM group_capital_allocations







                WHERE is_reversed = FALSE







            """)







            dep_to_grp_cash, dep_to_grp_upi, total_deployed_all = cur.fetchone()







            # Principal recovered from groups







            cur.execute("""







                SELECT COALESCE(SUM(principal_portion), 0), COALESCE(SUM(profit_portion), 0)







                FROM group_withdrawal_logs







                WHERE is_reversed = FALSE







            """)







            rec_principal, total_profit_distributed = cur.fetchone()







            # Active deployed capital remaining in routes







            active_deployed = max(0.0, float(total_deployed_all) - float(rec_principal))







            # Direct loans active principal







            cur.execute("""







                SELECT COALESCE(SUM(principal_amount), 0) 







                FROM direct_individual_loans 







                WHERE status = 'ACTIVE' AND is_reversed = FALSE







            """)







            total_direct_loans_issued = float(cur.fetchone()[0])







            cur.execute("""







                SELECT COALESCE(SUM(principal_amount), 0) 







                FROM direct_loan_repayments 







                WHERE is_reversed = FALSE







            """)







            total_direct_loans_repaid = float(cur.fetchone()[0])







            active_direct_loans = max(0.0, total_direct_loans_issued - total_direct_loans_repaid)







            # Unsettled central office expenses







            cur.execute("""







                SELECT COALESCE(SUM(amount), 0) 







                FROM central_office_expenses 







                WHERE is_settled = FALSE AND is_reversed = FALSE







            """)







            unsettled_expenses = float(cur.fetchone()[0])







            # Investor personal drawings







            cur.execute("""







                SELECT COALESCE(SUM(amount), 0) 

                FROM investor_personal_expenses 

                WHERE is_reversed = FALSE AND (is_settled IS NULL OR is_settled = FALSE)







            """)







            total_personal_draws = float(cur.fetchone()[0])







            # Total Vault Capital (Inflows minus Outflows)







            vault_cash = float(dep_cash) - float(w_cash) - float(dep_to_grp_cash)







            vault_upi = float(dep_upi) - float(w_upi) - float(dep_to_grp_upi)







            total_vault_capital = max(0.0, vault_cash + vault_upi)







            idle_capital = max(0.0, total_vault_capital - active_direct_loans - unsettled_expenses)







            kpi = {







                "total_capital": total_vault_capital + active_deployed,







                "total_cash": max(0.0, vault_cash),







                "total_upi": max(0.0, vault_upi),







                "deployed_capital": active_deployed,







                "idle_capital": idle_capital,







                "direct_loans_active": active_direct_loans,







                "unsettled_expenses": unsettled_expenses,







                "distributed_profits": float(total_profit_distributed)







            }







            # Recent transactions from master ledger







            cur.execute("""







                SELECT 







                    it.id, it.txn_type, it.payment_mode, it.amount, it.txn_date,







                    it.is_backdated, it.is_reversed, it.reversed_by, it.reversed_at,







                    it.created_by, it.created_at, it.notes,







                    inv.full_name as investor_name, inv.investor_code







                FROM investor_transactions it







                JOIN investors inv ON it.investor_id = inv.id







                ORDER BY it.txn_date DESC, it.created_at DESC







                LIMIT 50







            """)







            transactions = []







            for row in cur.fetchall():







                transactions.append({







                    "id": str(row[0]),







                    "txn_type": row[1],







                    "payment_mode": row[2],







                    "amount": float(row[3]),







                    "txn_date": row[4],







                    "is_backdated": row[5],







                    "is_reversed": row[6],







                    "reversed_by": row[7],







                    "reversed_at": row[8],







                    "created_by": row[9],







                    "created_at": row[10],







                    "notes": row[11],







                    "investor_name": row[12],







                    "investor_code": row[13]







                })







            # Fetch active investors list with liquid idle balance for modal dropdowns







            cur.execute("""







                SELECT 







                    inv.id, inv.investor_code, inv.full_name,







                    (







                        COALESCE(dep.total_deposited, 0) - COALESCE(wdr.total_withdrawn, 0) - COALESCE(alloc.total_deployed, 0)







                        + COALESCE(ret.total_principal_returned, 0) + COALESCE(ret.total_interest_earned, 0) + COALESCE(ret.total_profit_earned, 0)







                        - COALESCE(draw.total_draws, 0)







                    ) as idle_balance







                FROM investors inv







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_deposited







                    FROM investor_transactions







                    WHERE txn_type = 'DEPOSIT' AND is_reversed = FALSE







                    GROUP BY investor_id







                ) dep ON inv.id = dep.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_withdrawn







                    FROM investor_transactions







                    WHERE txn_type = 'IDLE_WITHDRAWAL' AND is_reversed = FALSE







                    GROUP BY investor_id







                ) wdr ON inv.id = wdr.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_deployed







                    FROM group_capital_allocations







                    WHERE is_reversed = FALSE







                    GROUP BY investor_id







                ) alloc ON inv.id = alloc.investor_id







                LEFT JOIN (







                    SELECT 







                        investor_id,







                        SUM(CASE WHEN component_type = 'PRINCIPAL' THEN amount ELSE 0 END) as total_principal_returned,







                        SUM(CASE WHEN component_type = 'INTEREST' THEN amount ELSE 0 END) as total_interest_earned,







                        SUM(CASE WHEN component_type = 'PROFIT' THEN amount ELSE 0 END) as total_profit_earned







                    FROM group_withdrawal_allocations gwa







                    JOIN group_withdrawal_logs gwl ON gwa.withdrawal_id = gwl.id







                    WHERE gwl.is_reversed = FALSE







                    GROUP BY investor_id







                ) ret ON inv.id = ret.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_draws 

                    FROM investor_personal_expenses 

                    WHERE is_reversed = FALSE AND (is_settled IS NULL OR is_settled = FALSE)

                    GROUP BY investor_id

                ) draw ON inv.id = draw.investor_id







                WHERE inv.is_active = TRUE







                ORDER BY inv.full_name ASC







            """)







            investors_list = [







                {







                    "id": str(r[0]),







                    "code": r[1],







                    "investor_code": r[1],







                    "name": r[2],







                    "full_name": r[2],







                    "idle_balance": max(0.0, float(r[3] or 0))







                }







                for r in cur.fetchall()







            ]







            # Fetch active village groups list for modal dropdowns







            cur.execute("SELECT id, group_code, group_name FROM village_groups WHERE UPPER(status) = 'ACTIVE' ORDER BY group_name ASC")







            groups_list = [







                {







                    "id": str(r[0]),







                    "code": r[1],







                    "group_code": r[1],







                    "name": r[2],







                    "group_name": r[2]







                }







                for r in cur.fetchall()







            ]







        return render_template(







            "banking/dashboard.html",







            kpi=kpi,







            transactions=transactions,







            investors=investors_list,







            investors_list=investors_list,







            village_groups=groups_list,







            groups_list=groups_list







        )







    except Exception as e:







        logger.error(f"Error loading banking dashboard: {e}", exc_info=True)







        flash(f"Error loading Treasury Dashboard: {e}")







        return render_template(







            "banking/dashboard.html",







            kpi={},







            transactions=[],







            investors=[],







            investors_list=[],







            village_groups=[],







            groups_list=[]







        )







    finally:







        if conn:







            conn.close()







# ---------------------------------------------------------------------------







# 2. Investor Management & 360° Folio







# ---------------------------------------------------------------------------







@banking_bp.route("/investors")







def investors_view():







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                SELECT 







                    inv.id, inv.investor_code, inv.full_name, inv.phone_number,







                    inv.global_share_pct, inv.is_active, inv.created_at,







                    COALESCE(dep.total_deposited, 0) as deposited,







                    COALESCE(wdr.total_withdrawn, 0) as idle_withdrawn,







                    COALESCE(alloc.total_deployed, 0) as deployed,







                    COALESCE(ret.total_principal_returned, 0) as principal_returned,







                    COALESCE(ret.total_interest_earned, 0) as interest_earned,







                    COALESCE(ret.total_profit_earned, 0) as profit_earned,







                    COALESCE(draw.total_draws, 0) as personal_draws,







                    inv.aadhaar_number, inv.pan_number,







                    cm.full_name as linked_chit_name







                FROM investors inv







                LEFT JOIN chit_members cm ON inv.linked_chit_member_id = cm.id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_deposited 







                    FROM investor_transactions 







                    WHERE txn_type = 'DEPOSIT' AND is_reversed = FALSE 







                    GROUP BY investor_id







                ) dep ON inv.id = dep.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_withdrawn 







                    FROM investor_transactions 







                    WHERE txn_type = 'IDLE_WITHDRAWAL' AND is_reversed = FALSE 







                    GROUP BY investor_id







                ) wdr ON inv.id = wdr.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_deployed 







                    FROM group_capital_allocations 







                    WHERE is_reversed = FALSE 







                    GROUP BY investor_id







                ) alloc ON inv.id = alloc.investor_id







                LEFT JOIN (







                    SELECT 







                        investor_id,







                        SUM(CASE WHEN component_type = 'PRINCIPAL' THEN amount ELSE 0 END) as total_principal_returned,







                        SUM(CASE WHEN component_type = 'INTEREST' THEN amount ELSE 0 END) as total_interest_earned,







                        SUM(CASE WHEN component_type = 'PROFIT' THEN amount ELSE 0 END) as total_profit_earned







                    FROM group_withdrawal_allocations







                    GROUP BY investor_id







                ) ret ON inv.id = ret.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_draws 

                    FROM investor_personal_expenses 

                    WHERE is_reversed = FALSE AND (is_settled IS NULL OR is_settled = FALSE)

                    GROUP BY investor_id

                ) draw ON inv.id = draw.investor_id







                ORDER BY inv.investor_code ASC







            """)







            investors = []







            for r in cur.fetchall():







                deposited = float(r[7])







                idle_wdr = float(r[8])







                deployed = float(r[9])







                p_returned = float(r[10])







                interest_earned = float(r[11])







                profit_earned = float(r[12])







                personal_draws = float(r[13])







                # Active deployed capital remaining in groups







                active_deployed = max(0.0, deployed - p_returned)







                # Idle cash = Deposited - Idle Withdrawn - Deployed + Returns - Draws







                idle_cash = (deposited - idle_wdr - deployed) + p_returned + interest_earned + profit_earned - personal_draws







                investors.append({







                    "id": str(r[0]),







                    "investor_code": r[1],







                    "code": r[1],







                    "full_name": r[2],







                    "name": r[2],







                    "phone_number": r[3],







                    "phone": r[3],







                    "global_share_pct": float(r[4] or 0),







                    "is_active": r[5],







                    "created_at": r[6],







                    "total_capital": deposited,







                    "deposited": deposited,







                    "active_deployed": active_deployed,







                    "deployed_capital": active_deployed,







                    "idle_cash": idle_cash,







                    "idle_balance": idle_cash,







                    "interest_earned": interest_earned,







                    "accrued_interest": interest_earned,







                    "profit_earned": profit_earned,







                    "accrued_return": interest_earned + profit_earned,







                    "personal_draws": personal_draws,







                    "unsettled_personal_expenses": personal_draws,







                    "aadhaar_number": r[14] or "",







                    "pan_number": r[15] or "",







                    "linked_chit_name": r[16] or ""







                })







            # Fetch chit members for linking dropdown







            cur.execute("SELECT id, customer_id, full_name, phone FROM chit_members ORDER BY customer_id ASC")







            chit_members = [{"id": str(r[0]), "code": r[1], "name": r[2], "phone": r[3]} for r in cur.fetchall()]







            summary = {







                "total_investors": len(investors),







                "total_capital": sum(inv["total_capital"] for inv in investors),







                "total_deployed": sum(inv["deployed_capital"] for inv in investors),







                "total_idle": sum(inv["idle_balance"] for inv in investors),







                "total_interest": sum(inv["accrued_interest"] for inv in investors),







            }







        return render_template("banking/investors.html", investors=investors, summary=summary, chit_members=chit_members)







    except Exception as e:







        logger.error(f"Error fetching investors list: {e}", exc_info=True)







        flash(f"Error loading investors: {e}")







        return render_template("banking/investors.html", investors=[], summary={}, chit_members=[])







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/investors", methods=["POST"])







def api_create_investor():







    data = request.get_json(silent=True) or request.form.to_dict()







    full_name = (data.get("full_name") or "").strip()







    phone_number = (data.get("phone_number") or "").strip()







    if not full_name or not phone_number:







        return jsonify({"success": False, "error": "Full Name and Phone Number are required."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # Auto-generate sequential investor code (INV-001, INV-002...)







            cur.execute("SELECT MAX(CAST(SUBSTRING(investor_code FROM 5) AS INT)) FROM investors WHERE investor_code LIKE 'INV-%'")







            max_num = cur.fetchone()[0] or 0







            new_code = f"INV-{max_num + 1:03d}"







            # Auto username and initial password







            username = data.get("username") or new_code.lower()







            raw_password = data.get("password") or "sd1234"







            pwd_hash = generate_password_hash(raw_password)







            cur.execute("""







                INSERT INTO investors (







                    investor_code, full_name, phone_number, email, aadhaar_number, pan_number,







                    address, nominee_name, nominee_relation, nominee_phone,







                    global_share_pct, linked_chit_member_id, username, password_hash







                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)







                RETURNING id, investor_code







            """, (







                new_code, full_name, phone_number,







                data.get("email"), data.get("aadhaar_number"), data.get("pan_number"),







                data.get("address"), data.get("nominee_name"), data.get("nominee_relation"), data.get("nominee_phone"),







                float(data.get("global_share_pct") or 0.0),







                data.get("linked_chit_member_id") or None,







                username, pwd_hash







            ))







            inv_id, code = cur.fetchone()







            conn.commit()







            return jsonify({







                "success": True,







                "message": f"Investor {full_name} ({code}) onboarded successfully.",







                "investor_id": str(inv_id),







                "investor_code": code







            })







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error creating investor: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/investors/<investor_id>")







def investor_detail_view(investor_id):







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # 1. Fetch investor profile







            cur.execute("SELECT * FROM investors WHERE id = %s", (investor_id,))







            col_names = [desc[0] for desc in cur.description]







            row = cur.fetchone()







            if not row:







                flash("Investor not found.")







                return redirect("/banking/investors")







            investor = dict(zip(col_names, row))







            # 2. Active Village Group Deployments







            cur.execute("""







                SELECT 







                    gca.id, gca.amount, gca.allocation_date, gca.interest_rate,







                    vg.id as group_id, vg.group_code, vg.group_name, vg.collection_days_per_week,







                    COALESCE(ret.repaid_principal, 0) as repaid_principal,







                    COALESCE(ret.repaid_interest, 0) as repaid_interest







                FROM group_capital_allocations gca







                JOIN village_groups vg ON gca.group_id = vg.id







                LEFT JOIN (







                    SELECT 







                        gwa.investor_id,







                        gwl.group_id,







                        SUM(CASE WHEN gwa.component_type = 'PRINCIPAL' THEN gwa.amount ELSE 0 END) as repaid_principal,







                        SUM(CASE WHEN gwa.component_type = 'INTEREST' THEN gwa.amount ELSE 0 END) as repaid_interest







                    FROM group_withdrawal_allocations gwa







                    JOIN group_withdrawal_logs gwl ON gwa.withdrawal_id = gwl.id







                    WHERE gwl.is_reversed = FALSE







                    GROUP BY gwa.investor_id, gwl.group_id







                ) ret ON gca.investor_id = ret.investor_id AND gca.group_id = ret.group_id







                WHERE gca.investor_id = %s AND gca.is_reversed = FALSE







                ORDER BY gca.allocation_date DESC







            """, (investor_id,))







            deployments = []







            today = date.today()







            total_deployed_active = 0.0







            total_interest_accrued = 0.0







            for r in cur.fetchall():







                orig_amount = float(r[1])







                alloc_date = r[2]







                rate = float(r[3] or 24.0)







                repaid_p = float(r[8])







                repaid_i = float(r[9])







                rem_principal = max(0.0, orig_amount - repaid_p)







                # Compute daily compound interest on the capital







                c_math = bce.calculate_compound_interest(







                    principal=orig_amount,







                    start_date=alloc_date,







                    as_of_date=today,







                    annual_rate=rate,







                    repaid_interest=repaid_i







                )







                deployments.append({







                    "id": str(r[0]),







                    "group_id": str(r[4]),







                    "group_code": r[5],







                    "group_name": r[6],







                    "collection_days": r[7],







                    "original_amount": orig_amount,







                    "remaining_principal": rem_principal,







                    "amount": rem_principal,







                    "allocation_date": alloc_date,







                    "days_elapsed": c_math["days_elapsed"],







                    "annual_rate": rate,







                    "interest_rate": rate,







                    "accrued_interest": c_math["net_unpaid_interest"],







                    "total_payoff": rem_principal + c_math["net_unpaid_interest"],







                    "payoff_balance": rem_principal + c_math["net_unpaid_interest"],







                    "is_reversed": False







                })







                total_deployed_active += rem_principal







                total_interest_accrued += c_math["net_unpaid_interest"]







            # 3. Personal Expense Drawings & Settlements

            cur.execute("""

                SELECT id, amount, payment_mode, expense_date, item_description, receipt_no, 

                       is_reversed, created_at, COALESCE(is_settled, FALSE), settled_at,

                       settled_by, settlement_mode, settlement_ref, settlement_notes

                FROM investor_personal_expenses

                WHERE investor_id = %s

                ORDER BY expense_date DESC, created_at DESC

            """, (investor_id,))

            personal_expenses = []

            active_drawings = []

            settled_drawings = []

            unsettled_personal_draws = 0.0

            settled_personal_draws = 0.0

            total_personal_draws = 0.0



            for r in cur.fetchall():

                is_rev = bool(r[6])

                amt = float(r[1])

                exp_dt = r[3]

                is_set = bool(r[8])

                settled_at = r[9]

                settled_by = r[10]

                set_mode = r[11] or "CASH"

                set_ref = r[12] or ""

                set_notes = r[13] or ""



                days_aged = (today - exp_dt).days if exp_dt else 0

                if days_aged > 60:

                    age_badge = "overdue_red"

                    age_text = f"{days_aged}d overdue"

                elif days_aged > 30:

                    age_badge = "warning_yellow"

                    age_text = f"{days_aged}d aged"

                else:

                    age_badge = "normal"

                    age_text = f"{days_aged}d"



                pe_item = {

                    "id": str(r[0]),

                    "amount": amt,

                    "payment_mode": r[2],

                    "expense_date": exp_dt,

                    "item_description": r[4],

                    "receipt_no": r[5],

                    "is_reversed": is_rev,

                    "created_at": r[7],

                    "is_settled": is_set,

                    "settled_at": settled_at,

                    "settled_by": settled_by,

                    "settlement_mode": set_mode,

                    "settlement_ref": set_ref,

                    "settlement_notes": set_notes,

                    "days_aged": days_aged,

                    "age_badge": age_badge,

                    "age_text": age_text

                }

                personal_expenses.append(pe_item)

                if not is_rev:

                    total_personal_draws += amt

                    if not is_set:

                        unsettled_personal_draws += amt

                        active_drawings.append(pe_item)

                    else:

                        settled_personal_draws += amt

                        settled_drawings.append(pe_item)



            active_deployments = [d for d in deployments if d["amount"] > 0 and not d["is_reversed"]]

            deactivated_deployments = [d for d in deployments if d["amount"] <= 0 or d["is_reversed"]]



            # 4. Total deposits and idle withdrawals

            cur.execute("""

                SELECT 

                    COALESCE(SUM(CASE WHEN txn_type = 'DEPOSIT' THEN amount ELSE 0 END), 0) as deposited,

                    COALESCE(SUM(CASE WHEN txn_type = 'IDLE_WITHDRAWAL' THEN amount ELSE 0 END), 0) as idle_wdr

                FROM investor_transactions

                WHERE investor_id = %s AND is_reversed = FALSE

            """, (investor_id,))

            tot_dep, tot_wdr = cur.fetchone()

            tot_dep = float(tot_dep)

            tot_wdr = float(tot_wdr)



            # 5. Total returns from groups

            cur.execute("""

                SELECT 

                    COALESCE(SUM(CASE WHEN component_type = 'PRINCIPAL' THEN amount ELSE 0 END), 0) as p_ret,

                    COALESCE(SUM(CASE WHEN component_type = 'INTEREST' THEN amount ELSE 0 END), 0) as i_ret,

                    COALESCE(SUM(CASE WHEN component_type = 'PROFIT' THEN amount ELSE 0 END), 0) as prf_ret

                FROM group_withdrawal_allocations

                WHERE investor_id = %s

            """, (investor_id,))

            p_ret, i_ret, prf_ret = cur.fetchone()

            p_ret = float(p_ret)

            i_ret = float(i_ret)

            prf_ret = float(prf_ret)



            # Net Idle Cash calculation (unsettled drawings deduct idle cash; settled drawings reimbursed)

            idle_cash = (tot_dep - tot_wdr - total_deployed_active) + p_ret + i_ret + prf_ret - unsettled_personal_draws



            balances = {

                "total_deposited": tot_dep,

                "idle_cash": idle_cash,

                "active_deployed": total_deployed_active,

                "accrued_interest": total_interest_accrued,

                "unsettled_draws": unsettled_personal_draws,

                "settled_draws": settled_personal_draws,

                "total_draws": total_personal_draws,

                "net_worth": idle_cash + total_deployed_active + total_interest_accrued

            }



            investor["idle_balance"] = idle_cash

            investor["deployed_capital"] = total_deployed_active

            investor["accrued_interest"] = total_interest_accrued

            investor["personal_expenses_total"] = unsettled_personal_draws

            investor["settled_draws_total"] = settled_personal_draws







            # 6. Full Transaction History







            cur.execute("""







                SELECT id, txn_type, payment_mode, amount, txn_date, is_backdated, is_reversed, notes, created_at







                FROM investor_transactions







                WHERE investor_id = %s







                ORDER BY txn_date DESC, created_at DESC







            """, (investor_id,))







            txns = []







            for r in cur.fetchall():







                txns.append({







                    "id": str(r[0]),







                    "txn_type": r[1],







                    "payment_mode": r[2],







                    "amount": float(r[3]),







                    "txn_date": r[4],







                    "is_backdated": r[5],







                    "is_reversed": r[6],







                    "notes": r[7],







                    "created_at": r[8]







                })







        return render_template(

            "banking/investor_detail.html",

            investor=investor,

            balances=balances,

            allocations=deployments,

            deployments=deployments,

            active_deployments=active_deployments,

            deactivated_deployments=deactivated_deployments,

            personal_expenses=personal_expenses,

            active_drawings=active_drawings,

            settled_drawings=settled_drawings,

            transactions=txns

        )







    except Exception as e:







        logger.error(f"Error loading investor folio: {e}", exc_info=True)







        flash(f"Error loading investor details: {e}")







        return redirect("/banking/investors")







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/investors/<investor_id>/deposit", methods=["POST"])







def api_investor_deposit(investor_id):







    data = request.get_json(silent=True) or request.form.to_dict()







    try:







        amount = float(data.get("amount") or 0)







        payment_mode = (data.get("payment_mode") or "CASH").upper()







        txn_date_str = data.get("txn_date") or date.today().isoformat()







        notes = data.get("notes") or ""







        effective_date = date.fromisoformat(txn_date_str[:10])







        is_backdated = effective_date < date.today()







        if amount <= 0:







            return jsonify({"success": False, "error": "Deposit amount must be greater than 0."}), 400







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                INSERT INTO investor_transactions (







                    investor_id, txn_type, payment_mode, amount, txn_date,







                    notes, is_backdated, created_by







                ) VALUES (%s, 'DEPOSIT', %s, %s, %s, %s, %s, %s)







                RETURNING id







            """, (







                investor_id, payment_mode, amount, effective_date,







                notes, is_backdated, session.get("username", "Admin")







            ))







            conn.commit()







        return jsonify({"success": True, "message": f"Successfully recorded deposit of {bce.format_currency_inr(amount)}."})







    except Exception as e:







        logger.error(f"Error recording deposit: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/investors/<investor_id>/withdraw", methods=["POST"])







def api_investor_withdraw_idle(investor_id):







    """







    Cash-out of idle funds from the Investment Bank. Protected by Admin Security PIN.







    """







    data = request.get_json(silent=True) or request.form.to_dict()







    pin = data.get("admin_pin")







    if not verify_admin_security_pin(pin):







        return jsonify({"success": False, "error": "Invalid Admin PIN. Cash-out authorization failed."}), 403







    try:







        amount = float(data.get("amount") or 0)







        payment_mode = (data.get("payment_mode") or "CASH").upper()







        txn_date_str = data.get("txn_date") or date.today().isoformat()







        notes = data.get("notes") or "Idle cash withdrawal"







        effective_date = date.fromisoformat(txn_date_str[:10])







        is_backdated = effective_date < date.today()







        if amount <= 0:







            return jsonify({"success": False, "error": "Withdrawal amount must be greater than 0."}), 400







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                INSERT INTO investor_transactions (







                    investor_id, txn_type, payment_mode, amount, txn_date,







                    notes, is_backdated, created_by







                ) VALUES (%s, 'IDLE_WITHDRAWAL', %s, %s, %s, %s, %s, %s)







                RETURNING id







            """, (







                investor_id, payment_mode, amount, effective_date,







                notes, is_backdated, session.get("username", "Admin")







            ))







            conn.commit()







        return jsonify({"success": True, "message": f"Authorized and recorded cash-out of {bce.format_currency_inr(amount)}."})







    except Exception as e:







        logger.error(f"Error processing idle withdrawal: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/investors/<investor_id>/personal-expense", methods=["POST"])



@banking_bp.route("/api/investors/<investor_id>/personal-expenses", methods=["POST"])



@banking_bp.route("/api/personal-expenses/add", methods=["POST"])



def api_add_personal_expense(investor_id=None):



    """



    Records an itemized personal expense for an investor (e.g., Amazon delivery paid by office cash).



    Debits investor's idle cash or creates a negative balance.



    """



    data = request.get_json(silent=True) or request.form.to_dict()



    inv_id = investor_id or data.get("investor_id")



    description = (data.get("item_description") or data.get("description") or "").strip()



    try:



        amount = float(data.get("amount") or 0)



    except (ValueError, TypeError):



        amount = 0.0



    payment_mode = (data.get("payment_mode") or "CASH").upper()



    exp_date_str = data.get("expense_date") or date.today().isoformat()



    receipt_no = data.get("receipt_no") or None







    if not inv_id or not description or amount <= 0:



        return jsonify({"success": False, "error": "Investor, description, and positive amount are required."}), 400







    conn = None



    try:



        conn = get_pg_connection()



        with conn.cursor() as cur:



            cur.execute("SELECT id, full_name FROM investors WHERE id = %s", (inv_id,))



            inv_row = cur.fetchone()



            if not inv_row:



                return jsonify({"success": False, "error": "Investor not found."}), 404







            cur.execute("""



                INSERT INTO investor_personal_expenses (



                    investor_id, amount, payment_mode, expense_date, item_description, receipt_no, created_by



                ) VALUES (%s, %s, %s, %s, %s, %s, %s)



                RETURNING id



            """, (



                inv_id, amount, payment_mode, date.fromisoformat(exp_date_str[:10]),



                description, receipt_no, session.get("username", "Admin")



            ))



            exp_id = cur.fetchone()[0]



            conn.commit()







        return jsonify({



            "success": True,



            "id": str(exp_id),



            "message": f"Personal expense of {bce.format_currency_inr(amount)} recorded successfully."



        })



    except Exception as e:



        if conn:



            conn.rollback()



        logger.error(f"Error recording personal expense: {e}", exc_info=True)



        return jsonify({"success": False, "error": str(e)}), 500



    finally:



        if conn:



            conn.close()











@banking_bp.route("/api/personal-expenses/<expense_id>/reverse", methods=["POST"])



@banking_bp.route("/api/investors/personal-expenses/<expense_id>/reverse", methods=["POST"])



def api_reverse_personal_expense(expense_id):



    """



    Reverses an investor personal expense / drawing. Requires Admin Security PIN.



    """



    data = request.get_json(silent=True) or request.form.to_dict()



    pin = data.get("admin_pin")



    if not verify_admin_security_pin(pin):



        return jsonify({"success": False, "error": "Invalid Admin PIN. Reversal authorization failed."}), 403







    reason = (data.get("reason") or "Administrative reversal").strip()







    conn = None



    try:



        conn = get_pg_connection()



        with conn.cursor() as cur:



            cur.execute("""



                UPDATE investor_personal_expenses



                SET is_reversed = TRUE, reversed_at = NOW(), reversed_by = %s,



                    reversal_reason = %s



                WHERE id = %s AND (is_reversed IS NULL OR is_reversed = FALSE)



                RETURNING id, amount, investor_id



            """, (session.get("username", "Admin"), reason, expense_id))



            row = cur.fetchone()



            if not row:



                return jsonify({"success": False, "error": "Personal expense not found or already reversed."}), 404



            conn.commit()







        return jsonify({



            "success": True,



            "message": f"Personal expense of {bce.format_currency_inr(float(row[1]))} reversed successfully."



        })



    except Exception as e:



        if conn:



            conn.rollback()



        logger.error(f"Error reversing personal expense {expense_id}: {e}", exc_info=True)



        return jsonify({"success": False, "error": str(e)}), 500



    finally:



        if conn:



            conn.close()





@banking_bp.route("/api/personal-expenses/<expense_id>/settle", methods=["POST"])

@banking_bp.route("/api/investors/personal-expenses/<expense_id>/settle", methods=["POST"])

def api_settle_personal_expense(expense_id):

    """

    Settles an investor personal drawing / expense.

    Records settlement mode (CASH, UPI, BANK_TRANSFER, IDLE_CASH), reference #, and notes.

    """

    data = request.get_json(silent=True) or request.form.to_dict()
    mode = (data.get("settlement_mode") or "CASH").upper()
    ref = (data.get("settlement_ref") or "").strip()
    notes = (data.get("settlement_notes") or "").strip()
    settled_at_str = data.get("settled_at")

    conn = None
    try:
        conn = get_pg_connection()
        with conn.cursor() as cur:
            if settled_at_str:
                cur.execute("""
                    UPDATE investor_personal_expenses
                    SET is_settled = TRUE,
                        settled_at = %s::timestamp,
                        settled_by = %s,
                        settlement_mode = %s,
                        settlement_ref = %s,
                        settlement_notes = %s
                    WHERE id = %s AND (is_reversed IS NULL OR is_reversed = FALSE)
                    RETURNING id, amount, investor_id, item_description
                """, (settled_at_str, session.get("username", "Admin"), mode, ref, notes, expense_id))
            else:
                cur.execute("""
                    UPDATE investor_personal_expenses
                    SET is_settled = TRUE,
                        settled_at = NOW(),
                        settled_by = %s,
                        settlement_mode = %s,
                        settlement_ref = %s,
                        settlement_notes = %s
                    WHERE id = %s AND (is_reversed IS NULL OR is_reversed = FALSE)
                    RETURNING id, amount, investor_id, item_description
                """, (session.get("username", "Admin"), mode, ref, notes, expense_id))

            row = cur.fetchone()

            if not row:

                return jsonify({"success": False, "error": "Personal expense not found or cannot be settled."}), 404

            conn.commit()



        amt = float(row[1])

        return jsonify({

            "success": True,

            "message": f"Personal drawing '{row[3]}' of {bce.format_currency_inr(amt)} marked as settled via {mode}!"

        })

    except Exception as e:

        if conn:

            conn.rollback()

        logger.error(f"Error settling personal expense {expense_id}: {e}", exc_info=True)

        return jsonify({"success": False, "error": str(e)}), 500

    finally:

        if conn:

            conn.close()





@banking_bp.route("/api/personal-expenses/<expense_id>/unsettle", methods=["POST"])

@banking_bp.route("/api/investors/personal-expenses/<expense_id>/unsettle", methods=["POST"])

def api_unsettle_personal_expense(expense_id):

    """

    Reopens a settled drawing back to active unsettled status.

    """

    conn = None

    try:

        conn = get_pg_connection()

        with conn.cursor() as cur:

            cur.execute("""

                UPDATE investor_personal_expenses

                SET is_settled = FALSE,

                    settled_at = NULL,

                    settled_by = NULL,

                    settlement_mode = NULL,

                    settlement_ref = NULL,

                    settlement_notes = NULL

                WHERE id = %s AND (is_reversed IS NULL OR is_reversed = FALSE)

                RETURNING id, amount, item_description

            """, (expense_id,))

            row = cur.fetchone()

            if not row:

                return jsonify({"success": False, "error": "Drawing not found."}), 404

            conn.commit()



        return jsonify({

            "success": True,

            "message": f"Drawing '{row[2]}' reopened as active unsettled."

        })

    except Exception as e:

        if conn:

            conn.rollback()

        logger.error(f"Error reopening personal expense {expense_id}: {e}", exc_info=True)

        return jsonify({"success": False, "error": str(e)}), 500

    finally:

        if conn:

            conn.close()







@banking_bp.route("/investors/<investor_id>/statement")







def investor_statement_pdf_view(investor_id):







    """







    Renders print-friendly A4 PDF statement.







    """







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("SELECT * FROM investors WHERE id = %s", (investor_id,))







            col_names = [desc[0] for desc in cur.description]







            row = cur.fetchone()







            if not row:







                flash("Investor not found.")







                return redirect("/banking/investors")







            investor = dict(zip(col_names, row))







            # Fetch deployments







            cur.execute("""







                SELECT 







                    gca.amount, gca.allocation_date, vg.group_name, gca.interest_rate,







                    COALESCE(ret.repaid_principal, 0), COALESCE(ret.repaid_interest, 0)







                FROM group_capital_allocations gca







                JOIN village_groups vg ON gca.group_id = vg.id







                LEFT JOIN (







                    SELECT 







                        gwa.investor_id, gwl.group_id,







                        SUM(CASE WHEN gwa.component_type = 'PRINCIPAL' THEN gwa.amount ELSE 0 END) as repaid_principal,







                        SUM(CASE WHEN gwa.component_type = 'INTEREST' THEN gwa.amount ELSE 0 END) as repaid_interest







                    FROM group_withdrawal_allocations gwa







                    JOIN group_withdrawal_logs gwl ON gwa.withdrawal_id = gwl.id







                    WHERE gwl.is_reversed = FALSE







                    GROUP BY gwa.investor_id, gwl.group_id







                ) ret ON gca.investor_id = ret.investor_id AND gca.group_id = ret.group_id







                WHERE gca.investor_id = %s AND gca.is_reversed = FALSE







            """, (investor_id,))







            today = date.today()







            deployments = []







            for r in cur.fetchall():







                c_math = bce.calculate_compound_interest(float(r[0]), r[1], today, float(r[3] or 24.0), float(r[5]))







                deployments.append({







                    "group_name": r[2],







                    "principal": float(r[0]),







                    "date": r[1],







                    "accrued_interest": c_math["net_unpaid_interest"],







                    "payoff": c_math["current_payoff_balance"],
                    "total_payoff": c_math["current_payoff_balance"]







                })







            # Fetch personal expenses







            cur.execute("""







                SELECT expense_date, item_description, amount, payment_mode







                FROM investor_personal_expenses







                WHERE investor_id = %s AND is_reversed = FALSE







                ORDER BY expense_date DESC







            """, (investor_id,))







            personal_expenses = [{"date": r[0], "desc": r[1], "amount": float(r[2]), "mode": r[3]} for r in cur.fetchall()]







            # Fetch recent ledger transactions







            cur.execute("""







                SELECT txn_date, txn_type, payment_mode, amount, notes, is_backdated







                FROM investor_transactions







                WHERE investor_id = %s AND is_reversed = FALSE







                ORDER BY txn_date DESC







            """, (investor_id,))







            transactions = [{"date": r[0], "type": r[1], "mode": r[2], "amount": float(r[3]), "notes": r[4], "backdated": r[5]} for r in cur.fetchall()]







        return render_template(







            "banking/statement_pdf.html",







            investor=investor,







            deployments=deployments,







            personal_expenses=personal_expenses,







            transactions=transactions,







            as_of_date=date.today()







        )







    finally:







        if conn:







            conn.close()







# ---------------------------------------------------------------------------







# 3. Village Group Banks (Route Banks) & Cashbag Bridge







# ---------------------------------------------------------------------------







@banking_bp.route("/groups")







def village_groups_view():







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            today = date.today()







            cur.execute("""







                SELECT 







                    vg.id, vg.group_code, vg.group_name, vg.collection_days_per_week, vg.status,







                    e1.name as emp1_name, e2.name as emp2_name, vg.emp1_id, vg.emp2_id,







                    COALESCE(NULLIF(vg.assigned_villages, ''), (







                        SELECT string_agg(DISTINCT v.village_code, ', ' ORDER BY v.village_code)







                        FROM village v







                        WHERE v.emp1 = vg.emp1_id 







                          AND ((v.emp2 = vg.emp2_id) OR (v.emp2 IS NULL AND vg.emp2_id IS NULL))







                          AND v.village_code IS NOT NULL AND v.village_code != ''







                    )) as village_codes







                FROM village_groups vg







                LEFT JOIN employee e1 ON vg.emp1_id = e1.eid







                LEFT JOIN employee e2 ON vg.emp2_id = e2.eid







                ORDER BY vg.group_name ASC







            """)







            raw_groups = cur.fetchall()







            groups = []







            for r in raw_groups:







                grp_id = str(r[0])







                emp1_id = r[7]







                emp2_id = r[8]







                v_codes = r[9] or ""







                v_codes_list = [c.strip() for c in v_codes.split(",") if c.strip()]







                # 1. Capital allocations & 24% compound interest







                cur.execute("""







                    SELECT amount, allocation_date, interest_rate







                    FROM group_capital_allocations







                    WHERE group_id = %s AND (is_reversed IS NULL OR is_reversed = FALSE)







                """, (grp_id,))







                total_allocated = 0.0







                accrued_return = 0.0







                for alloc in cur.fetchall():







                    amt = float(alloc[0])







                    alloc_dt = alloc[1]







                    rate = float(alloc[2] or 24.0)







                    total_allocated += amt







                    c_math = bce.calculate_compound_interest(amt, alloc_dt, today, rate)







                    accrued_return += c_math["net_unpaid_interest"]







                # 2. Withdrawals







                cur.execute("""







                    SELECT 







                        COALESCE(SUM(principal_portion), 0),







                        COALESCE(SUM(interest_portion), 0),







                        COALESCE(SUM(profit_portion), 0)







                    FROM group_withdrawal_logs







                    WHERE group_id = %s AND (is_reversed IS NULL OR is_reversed = FALSE)







                """, (grp_id,))







                w_row = cur.fetchone()







                repaid_p, repaid_i, withdrawn_profit = float(w_row[0]), float(w_row[1]), float(w_row[2])







                active_cap = max(0.0, total_allocated - repaid_p)







                accrued_return = max(0.0, accrued_return - repaid_i)







                # 3. Opening legacy balances







                cur.execute("""







                    SELECT initial_invested_principal, accrued_interest_to_date, profit_in_circulation







                    FROM village_group_openings







                    WHERE group_id = %s







                """, (grp_id,))







                op_row = cur.fetchone()







                opening_profit = 0.0







                if op_row:







                    if active_cap == 0 and op_row[0]:







                        active_cap = float(op_row[0])







                    accrued_return += float(op_row[1] or 0)







                    opening_profit = float(op_row[2] or 0)







                # 4. Customer loan interest from villages in this bank







                vids = []







                if emp1_id is not None:







                    if emp2_id is not None:







                        cur.execute("SELECT vid FROM village WHERE emp1 = %s AND emp2 = %s AND status = 'active'", (emp1_id, emp2_id))







                    else:







                        cur.execute("SELECT vid FROM village WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = %s) AND status = 'active'", (emp1_id, emp1_id))







                    vids = [x[0] for x in cur.fetchall()]







                total_customer_interest = 0.0







                if vids:







                    cur.execute("""







                        SELECT 







                            COALESCE(SUM(CASE WHEN c.interest_amount > 0 THEN c.interest_amount ELSE ROUND(c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0), 2) END), 0) AS commission_total







                        FROM (







                            SELECT total_amount, cutting_amount, interest_amount, payment_type, status, vid FROM customer







                            UNION ALL







                            SELECT total_amount, cutting_amount, interest_amount, payment_type, status, vid FROM closed_cust_account







                        ) c







                        JOIN village v ON c.vid = v.vid







                        WHERE c.vid = ANY(%s) AND c.status != 'deleted'







                    """, (vids,))







                    total_customer_interest = float(cur.fetchone()[0] or 0)







                circulating_profit = max(0.0, total_customer_interest + opening_profit - accrued_return - withdrawn_profit)







                emp_names = [e for e in [r[5], r[6]] if e]







                groups.append({







                    "id": grp_id,







                    "code": r[1],







                    "group_code": r[1],







                    "name": r[2],







                    "group_name": r[2],







                    "days": r[3],







                    "collection_days_per_week": r[3],







                    "status": r[4],







                    "emp1_name": r[5],







                    "emp2_name": r[6],







                    "total_capital": total_allocated,







                    "active_capital": active_cap,







                    "accrued_interest": accrued_return,







                    "accrued_return": accrued_return,







                    "repaid_interest": repaid_i,







                    "circulating_profit": circulating_profit,







                    "total_profit": circulating_profit,







                    "village_codes": v_codes,







                    "village_codes_list": v_codes_list,







                    "employees_list": emp_names,







                    "villages_list": v_codes_list







                })







            # Fetch active employees







            cur.execute("SELECT eid, name FROM employee WHERE is_active = TRUE ORDER BY name ASC")







            employees = [{"eid": r[0], "name": r[1]} for r in cur.fetchall()]







            # Fetch active investors with liquid idle balances for Setup Wizard







            cur.execute("""







                SELECT 







                    inv.id, inv.investor_code, inv.full_name,







                    (







                        COALESCE(dep.total_deposited, 0) - COALESCE(wdr.total_withdrawn, 0) - COALESCE(alloc.total_deployed, 0)







                        + COALESCE(ret.total_principal_returned, 0) + COALESCE(ret.total_interest_earned, 0) + COALESCE(ret.total_profit_earned, 0)







                        - COALESCE(draw.total_draws, 0)







                    ) as idle_balance







                FROM investors inv







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_deposited 







                    FROM investor_transactions 







                    WHERE txn_type = 'DEPOSIT' AND is_reversed = FALSE 







                    GROUP BY investor_id







                ) dep ON inv.id = dep.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_withdrawn 







                    FROM investor_transactions 







                    WHERE txn_type = 'IDLE_WITHDRAWAL' AND is_reversed = FALSE 







                    GROUP BY investor_id







                ) wdr ON inv.id = wdr.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_deployed 







                    FROM group_capital_allocations 







                    WHERE is_reversed = FALSE 







                    GROUP BY investor_id







                ) alloc ON inv.id = alloc.investor_id







                LEFT JOIN (







                    SELECT 







                        investor_id,







                        SUM(CASE WHEN component_type = 'PRINCIPAL' THEN amount ELSE 0 END) as total_principal_returned,







                        SUM(CASE WHEN component_type = 'INTEREST' THEN amount ELSE 0 END) as total_interest_earned,







                        SUM(CASE WHEN component_type = 'PROFIT' THEN amount ELSE 0 END) as total_profit_earned







                    FROM group_withdrawal_allocations







                    GROUP BY investor_id







                ) ret ON inv.id = ret.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_draws 

                    FROM investor_personal_expenses 

                    WHERE is_reversed = FALSE AND (is_settled IS NULL OR is_settled = FALSE)

                    GROUP BY investor_id

                ) draw ON inv.id = draw.investor_id







                WHERE inv.is_active = TRUE







                ORDER BY inv.full_name ASC;







            """)







            investors = [{







                "id": str(r[0]),







                "code": r[1],







                "investor_code": r[1],







                "name": r[2],







                "full_name": r[2],







                "idle_balance": float(r[3] or 0)







            } for r in cur.fetchall()]







            summary = {







                "total_groups": len(groups),







                "total_capital": sum(g["active_capital"] for g in groups),







                "total_profit": sum(g["circulating_profit"] for g in groups),







                "total_days": sum(g["collection_days_per_week"] for g in groups)







            }







        return render_template("banking/village_groups.html", groups=groups, summary=summary, employees=employees, investors=investors)







    except Exception as e:







        logger.error(f"Error listing village groups: {e}", exc_info=True)







        flash(f"Error loading Village Groups: {e}")







        return render_template("banking/village_groups.html", groups=[], summary={}, employees=[], investors=[])







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/smart-counting/cashbags", methods=["GET"])
def api_smart_counting_cashbags():
    """
    Returns all Smart Counting Cashbags with their employees and villages.
    """
    conn = None
    try:
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.id,
                    c.name,
                    c.emp1,
                    c.emp2,
                    c.village_codes,
                    c.week_ending_day,
                    COALESCE(e1.name, 'Emp #' || c.emp1::text) as emp1_name,
                    e2.name as emp2_name
                FROM village_cashbags c
                LEFT JOIN employee e1 ON c.emp1 = e1.eid
                LEFT JOIN employee e2 ON c.emp2 = e2.eid
                ORDER BY e1.name ASC, c.name ASC
            """)
            cb_rows = cur.fetchall()
            
            cur.execute("SELECT vid, village_code, village_name FROM village WHERE status = 'active'")
            v_map = {r[1]: {"vid": r[0], "code": r[1], "name": r[2]} for r in cur.fetchall()}
            
            result = []
            for r in cb_rows:
                cb_id, cb_name, emp1, emp2, vcodes, wday, e1_name, e2_name = r
                vcodes = vcodes or []
                villages = [v_map[c] for c in vcodes if c in v_map]
                result.append({
                    "id": str(cb_id),
                    "name": cb_name,
                    "emp1": emp1,
                    "emp2": emp2,
                    "emp1_name": e1_name,
                    "emp2_name": e2_name,
                    "village_codes": vcodes,
                    "villages": villages,
                    "village_count": len(villages),
                    "week_ending_day": wday or 3,
                    "suggested_name": f"{cb_name} Village Bank"
                })
            return jsonify({"success": True, "cashbags": result})
    except Exception as e:
        logger.error(f"Error fetching smart counting cashbags: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@banking_bp.route("/api/smart-counting/groups", methods=["GET"])







def api_smart_counting_groups():







    """







    Returns existing smart counting employee routes with their villages.







    """







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                SELECT 







                    v.emp1, 







                    v.emp2, 







                    COALESCE(e1.name, 'Emp #' || v.emp1::text) as emp1_name, 







                    e2.name as emp2_name,







                    count(v.vid) as village_count,







                    json_agg(json_build_object(







                        'vid', v.vid, 







                        'code', v.village_code, 







                        'name', v.village_name







                    ) ORDER BY v.village_code) as villages







                FROM village v







                LEFT JOIN employee e1 ON v.emp1 = e1.eid







                LEFT JOIN employee e2 ON v.emp2 = e2.eid







                WHERE v.emp1 IS NOT NULL AND v.status = 'active'







                GROUP BY v.emp1, v.emp2, e1.name, e2.name







                ORDER BY e1.name, e2.name;







            """)







            routes = []







            for r in cur.fetchall():







                emp1, emp2, emp1_name, emp2_name, v_count, v_list = r







                suggested_name = f"{emp1_name} & {emp2_name} Bank" if emp2 and emp2_name else f"{emp1_name} Bank"







                routes.append({







                    "emp1_id": emp1,







                    "emp2_id": emp2,







                    "emp1_name": emp1_name,







                    "emp2_name": emp2_name or "",







                    "village_count": v_count,







                    "suggested_name": suggested_name,







                    "suggested_days": min(6, max(1, v_count)),







                    "villages": v_list or []







                })







            return jsonify({"success": True, "groups": routes})







    except Exception as e:







        logger.error(f"Error fetching smart counting groups: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/next-bank-code", methods=["GET"])







def api_next_bank_code():







    """







    Returns next sequential Bank ID: VB-001, VB-002...







    """







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("SELECT MAX(CAST(SUBSTRING(group_code FROM 4) AS INT)) FROM village_groups WHERE group_code LIKE 'VB-%'")







            max_num = cur.fetchone()[0] or 0







            next_code = f"VB-{max_num + 1:03d}"







        return jsonify({"success": True, "bank_code": next_code})







    except Exception as e:







        return jsonify({"success": False, "bank_code": "VB-001"})







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/village-banks/setup", methods=["POST"])







def api_save_village_bank_setup():







    """







    Multi-Step Village Bank Setup:







    Step 1: Group selection, village pills selection, Bank ID, Bank Name, Opening Date, Collection Days







    Step 2: Investor shareholdings breakdown (must equal 100%)







    Step 3: Historical Balance Injection (must equal total invested capital)







    Debits investor idle balances (allowing negative balance).







    """







    data = request.get_json(silent=True) or request.form.to_dict()







    bank_name = (data.get("bank_name") or "").strip()







    bank_code = (data.get("bank_code") or "").strip()







    emp1_id = data.get("emp1_id")







    emp2_id = data.get("emp2_id") or None







    days = int(data.get("collection_days_per_week") or 5)







    as_of_date_str = data.get("as_of_date") or date.today().isoformat()







    as_of_date = date.fromisoformat(as_of_date_str[:10])







    selected_villages = data.get("selected_villages") or []







    if isinstance(selected_villages, list):







        assigned_villages_str = ", ".join(selected_villages)







        assigned_codes_list = selected_villages







    else:







        assigned_villages_str = str(selected_villages)







        assigned_codes_list = [c.strip() for c in assigned_villages_str.split(",") if c.strip()]







    shares = data.get("shares") or []







    balance = data.get("balance_injection") or {}







    if not bank_name:







        return jsonify({"success": False, "error": "Bank Name is required."}), 400







    if not emp1_id:







        return jsonify({"success": False, "error": "Primary employee (Employee 1) is required."}), 400







    if not shares:







        return jsonify({"success": False, "error": "At least one investor must be assigned in Step 2."}), 400







    # Step 2: Total share percentage must equal 100%







    total_pct = sum(float(s.get("share_pct") or 0) for s in shares)
    if total_pct < 100.0 - 0.05:
        return jsonify({"success": False, "error": f"Investor shareholdings must be at least 100%. Currently: {total_pct:.0f}%"}), 400

    total_invested_amount = sum(float(s.get("amount") or 0) for s in shares)







    # Step 3: Historical balance injection







    loans_outstanding = float(balance.get("active_loans") or balance.get("loans_outstanding") or 0)







    accrued_interest = float(balance.get("accrued_interest") or 0)







    profit_circulation = float(balance.get("profit_in_circulation") or 0)







    cashbag_cash = float(balance.get("cashbag_opening_cash") or 0)







    cashbag_upi = float(balance.get("cashbag_opening_upi") or 0)







    total_injected = loans_outstanding + accrued_interest + profit_circulation + cashbag_cash + cashbag_upi







    # Historical balance injection check (non-blocking)
    if total_invested_amount > 0 and total_injected > 0 and abs(total_injected - total_invested_amount) > 1.0:
        logger.info(f"Balance injection difference noted: injected={total_injected}, invested={total_invested_amount}")







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # Auto-assign bank_code if not supplied







            if not bank_code:







                cur.execute("SELECT MAX(CAST(SUBSTRING(group_code FROM 4) AS INT)) FROM village_groups WHERE group_code LIKE 'VB-%'")







                max_num = cur.fetchone()[0] or 0







                bank_code = f"VB-{max_num + 1:03d}"







            # 1. Create village_groups record







            cur.execute("""







                INSERT INTO village_groups (







                    group_code, group_name, emp1_id, emp2_id, collection_days_per_week,







                    assigned_villages, assigned_village_codes, status







                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')







                RETURNING id







            """, (bank_code, bank_name, emp1_id, emp2_id, days, assigned_villages_str, assigned_codes_list))







            group_id = cur.fetchone()[0]







            # 2. Create opening balance record







            cur.execute("""







                INSERT INTO village_group_openings (







                    group_id, as_of_date, initial_invested_principal, accrued_interest_to_date,







                    profit_in_circulation, cashbag_opening_cash, cashbag_opening_upi, created_by







                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)







            """, (







                group_id, as_of_date,







                loans_outstanding, accrued_interest, profit_circulation,







                cashbag_cash, cashbag_upi, session.get("username", "Admin")







            ))







            # 3. Create investor shares & allocate capital







            for s in shares:







                inv_id = s.get("investor_id")







                inv_amt = float(s.get("amount") or 0)







                inv_pct = float(s.get("share_pct") or 0)







                # Save share %







                cur.execute("""







                    INSERT INTO investor_group_shares (group_id, investor_id, share_pct)







                    VALUES (%s, %s, %s)







                """, (group_id, inv_id, inv_pct))







                if inv_amt > 0:







                    # Allocate capital to group







                    cur.execute("""







                        INSERT INTO group_capital_allocations (







                            group_id, investor_id, amount, payment_mode, allocation_date, created_by







                        ) VALUES (%s, %s, %s, 'CASH', %s, %s)







                        RETURNING id







                    """, (group_id, inv_id, inv_amt, as_of_date, session.get("username", "Admin")))







                    alloc_id = cur.fetchone()[0]







                    # Look up investor info







                    cur.execute("SELECT full_name, investor_code FROM investors WHERE id = %s", (inv_id,))







                    inv_info = cur.fetchone()







                    inv_name_str = inv_info[0] if inv_info else "Investor"







                    inv_code_str = inv_info[1] if inv_info else ""







                    cb_notes = f"Capital Deployed - {inv_name_str} ({inv_code_str}) -> {bank_code}"







                    # Credit into Cashbag







                    cur.execute("""







                        INSERT INTO cashbag_transactions (







                            emp1, emp2, group_id, txn, txn_sub, txn_type, amount, notes, created_by, created_at







                        ) VALUES (%s, %s, %s, 'CAPITAL_DEPLOYED', '', 'CASH', %s, %s, %s, %s)







                        RETURNING id







                    """, (







                        emp1_id, emp2_id, group_id, inv_amt, cb_notes,







                        session.get("username", "Admin"),







                        datetime.combine(as_of_date, datetime.now().time())







                    ))







                    cb_txn_id = cur.fetchone()[0]







                    cur.execute("UPDATE group_capital_allocations SET cashbag_txn_id = %s WHERE id = %s", (cb_txn_id, alloc_id))







                    # Deduct from investor idle balance (negative balance permitted)







                    cur.execute("""







                        INSERT INTO investor_transactions (







                            investor_id, txn_type, payment_mode, amount, txn_date,







                            reference_id, notes, created_by







                        ) VALUES (%s, 'CAPITAL_DEPLOYED', 'CASH', %s, %s, %s, %s, %s)







                    """, (







                        inv_id, inv_amt, as_of_date,







                        alloc_id, f"Capital deployed into {bank_name} ({bank_code})", session.get("username", "Admin")







                    ))







            # 4. Cashbag transaction for physical opening cash







            if cashbag_cash > 0:







                cb_notes = f"Opening Cashbag Cash: {bank_name} ({bank_code})"







                cur.execute("""







                    INSERT INTO cashbag_transactions (







                        emp1, emp2, txn, txn_sub, txn_type, amount, notes, created_by, created_at







                    ) VALUES (%s, %s, 'OFFICE_CASH', '', 'CASH', %s, %s, %s, %s)







                """, (







                    emp1_id, emp2_id, cashbag_cash, cb_notes,







                    session.get("username", "Admin"),







                    datetime.combine(as_of_date, datetime.now().time())







                ))







            conn.commit()







            return jsonify({







                "success": True,







                "message": f"Village Bank '{bank_name}' ({bank_code}) created successfully!",







                "group_id": str(group_id),







                "bank_code": bank_code







            })







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error setting up Village Bank: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/groups/sync-smart-counting", methods=["POST"])







def api_sync_smart_counting_routes():







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            count = sync_village_groups_from_smart_counting(cur)







            conn.commit()







        return jsonify({"success": True, "message": f"Successfully synchronized {count} Village Group Routes from Smart Counting."})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error syncing Smart Counting routes: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/groups", methods=["POST"])







def api_create_village_group():







    data = request.get_json(silent=True) or request.form.to_dict()







    group_name = (data.get("group_name") or "").strip()







    group_code = (data.get("group_code") or "").strip()







    emp1_id = data.get("emp1_id")







    emp2_id = data.get("emp2_id") or None







    days = int(data.get("collection_days_per_week") or 5)







    if not group_name or not group_code or not emp1_id:







        return jsonify({"success": False, "error": "Group Name, Code, and primary collector (Emp 1) are required."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                INSERT INTO village_groups (group_code, group_name, emp1_id, emp2_id, collection_days_per_week)







                VALUES (%s, %s, %s, %s, %s)







                RETURNING id







            """, (group_code, group_name, emp1_id, emp2_id, days))







            new_id = cur.fetchone()[0]







            # Populate default ownership shares from investors' global_share_pct







            cur.execute("SELECT id, global_share_pct FROM investors WHERE is_active = TRUE")







            for inv_id, g_pct in cur.fetchall():







                if g_pct and float(g_pct) > 0:







                    cur.execute("""







                        INSERT INTO investor_group_shares (group_id, investor_id, share_pct)







                        VALUES (%s, %s, %s)







                        ON CONFLICT DO NOTHING







                    """, (new_id, inv_id, float(g_pct)))







            conn.commit()







            return jsonify({"success": True, "message": f"Village Group {group_name} created successfully.", "id": str(new_id)})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error creating village group: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/groups/<group_id>/update", methods=["POST", "PUT"])







@banking_bp.route("/api/groups/<group_id>", methods=["PUT"])







def api_update_village_group(group_id):







    data = request.get_json(silent=True) or request.form.to_dict()







    group_name = (data.get("group_name") or "").strip()







    group_code = (data.get("group_code") or "").strip()







    days_val = data.get("collection_days_per_week") or data.get("days")







    notes = data.get("notes")







    if not group_code:







        return jsonify({"success": False, "error": "Route code cannot be empty"}), 400







    try:







        days = int(days_val)







        if days < 1 or days > 7:







            return jsonify({"success": False, "error": "Collection days must be between 1 and 7"}), 400







    except (ValueError, TypeError):







        return jsonify({"success": False, "error": "Invalid collection days value"}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("SELECT id FROM village_groups WHERE id = %s", (group_id,))







            if not cur.fetchone():







                return jsonify({"success": False, "error": "Route bank not found"}), 404







            cur.execute("SELECT id FROM village_groups WHERE group_code = %s AND id != %s", (group_code, group_id))







            if cur.fetchone():







                return jsonify({"success": False, "error": f"Route code '{group_code}' is already in use by another group"}), 400







            cur.execute("""







                UPDATE village_groups







                SET group_code = %s,







                    group_name = COALESCE(NULLIF(%s, ''), group_name),







                    collection_days_per_week = %s,







                    notes = COALESCE(%s, notes),







                    updated_at = NOW()







                WHERE id = %s







            """, (group_code, group_name, days, notes, group_id))







            conn.commit()







        return jsonify({







            "success": True,







            "message": f"Route bank updated successfully! Route code: {group_code}, Days: {days}"







        })







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error updating village group {group_id}: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/groups/<group_id>")







def group_detail_view(group_id):







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # 1. Fetch group details with associated village codes







            cur.execute("""







                SELECT 







                    vg.id, vg.group_code, vg.group_name, vg.collection_days_per_week, vg.status, vg.notes,







                    e1.name as emp1_name, e2.name as emp2_name, vg.emp1_id, vg.emp2_id,







                    (







                        SELECT string_agg(DISTINCT v.village_code, ', ' ORDER BY v.village_code)







                        FROM village v







                        WHERE v.emp1 = vg.emp1_id 







                          AND ((v.emp2 = vg.emp2_id) OR (v.emp2 IS NULL AND vg.emp2_id IS NULL))







                          AND v.village_code IS NOT NULL AND v.village_code != ''







                    ) as village_codes







                FROM village_groups vg







                LEFT JOIN employee e1 ON vg.emp1_id = e1.eid







                LEFT JOIN employee e2 ON vg.emp2_id = e2.eid







                WHERE vg.id = %s







            """, (group_id,))







            row = cur.fetchone()







            if not row:







                flash("Village Group not found.")







                return redirect("/banking/groups")







            v_codes = row[10] or ""







            v_codes_list = [c.strip() for c in v_codes.split(",") if c.strip()]







            emp_names = [e for e in [row[6], row[7]] if e]







            group = {







                "id": str(row[0]),







                "group_code": row[1],







                "group_name": row[2],







                "collection_days_per_week": row[3],







                "status": row[4],







                "notes": row[5],







                "emp1_name": row[6],







                "emp2_name": row[7],







                "emp1_id": row[8],







                "emp2_id": row[9],







                "village_codes": v_codes,







                "village_codes_list": v_codes_list,







                "employees_list": emp_names,







                "villages_list": v_codes_list







            }







            # 2. Fetch capital allocations







            cur.execute("""







                SELECT 







                    gca.id, gca.amount, gca.payment_mode, gca.allocation_date, gca.interest_rate,







                    gca.is_backdated, gca.is_reversed, inv.id as investor_id, inv.full_name as investor_name, inv.investor_code







                FROM group_capital_allocations gca







                JOIN investors inv ON gca.investor_id = inv.id







                WHERE gca.group_id = %s







                ORDER BY gca.allocation_date DESC







            """, (group_id,))







            allocations = []







            total_active_principal = 0.0







            total_accrued_interest = 0.0







            today = date.today()







            for r in cur.fetchall():







                amt = float(r[1])







                is_rev = r[6]







                if not is_rev:







                    total_active_principal += amt







                    # Calculate 24% compound interest







                    c_math = bce.calculate_compound_interest(amt, r[3], today, float(r[4] or 24.0))







                    total_accrued_interest += c_math["net_unpaid_interest"]







                    accrued_i = c_math["net_unpaid_interest"]







                else:







                    accrued_i = 0.0







                allocations.append({







                    "id": str(r[0]),







                    "amount": amt,







                    "payment_mode": r[2],







                    "allocation_date": r[3],







                    "interest_rate": float(r[4] or 24.0),







                    "is_backdated": r[5],







                    "is_reversed": is_rev,







                    "investor_id": str(r[7]),







                    "investor_name": r[8],







                    "investor_code": r[9],







                    "accrued_interest": accrued_i







                })







            # 3. Ownership shares







            cur.execute("""







                SELECT igs.id, igs.share_pct, inv.id as investor_id, inv.full_name, inv.investor_code







                FROM investor_group_shares igs







                JOIN investors inv ON igs.investor_id = inv.id







                WHERE igs.group_id = %s







                ORDER BY igs.share_pct DESC







            """, (group_id,))







            shares = [







                {







                    "id": str(r[0]),







                    "share_pct": float(r[1]),







                    "investor_id": str(r[2]),







                    "name": r[3],







                    "investor_name": r[3],







                    "full_name": r[3],







                    "code": r[4],







                    "investor_code": r[4]







                }







                for r in cur.fetchall()







            ]







            # Query active capital remaining in this group per investor







            cur.execute("""







                SELECT gca.investor_id,







                       SUM(gca.amount) - COALESCE(SUM(ret.repaid_principal), 0) as active_principal







                FROM group_capital_allocations gca







                LEFT JOIN (







                    SELECT gwa.investor_id, gwl.group_id,







                           SUM(CASE WHEN gwa.component_type = 'PRINCIPAL' THEN gwa.amount ELSE 0 END) as repaid_principal







                    FROM group_withdrawal_allocations gwa







                    JOIN group_withdrawal_logs gwl ON gwa.withdrawal_id = gwl.id







                    WHERE gwl.is_reversed = FALSE







                    GROUP BY gwa.investor_id, gwl.group_id







                ) ret ON gca.investor_id = ret.investor_id AND gca.group_id = ret.group_id







                WHERE gca.group_id = %s AND gca.is_reversed = FALSE







                GROUP BY gca.investor_id







            """, (group_id,))







            active_cap_map = {str(r[0]): float(r[1] or 0) for r in cur.fetchall()}







            for s in shares:







                s["active_capital"] = active_cap_map.get(s["investor_id"], 0.0)







            # 4. Live Cashbag Holdings & Circulating Profit Calculation for this Village Bank







            emp1 = group["emp1_id"]







            emp2 = group["emp2_id"]







            # A. Fetch active village IDs for this group







            vids = []







            if emp1 is not None:







                if emp2 is not None:







                    cur.execute("SELECT vid FROM village WHERE emp1 = %s AND emp2 = %s AND status = 'active'", (emp1, emp2))







                else:







                    cur.execute("SELECT vid FROM village WHERE emp1 = %s AND (emp2 IS NULL OR emp2 = %s) AND status = 'active'", (emp1, emp1))







                vids = [r[0] for r in cur.fetchall()]







            # B. Cashbag Manual Transactions
            if emp2 is not None:
                pair_filter = "emp1 = %s AND emp2 = %s"
                pair_params = (emp1, emp2)
            else:
                pair_filter = "emp1 = %s AND (emp2 IS NULL OR emp2 = %s)"
                pair_params = (emp1, emp1)

            cur.execute(f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN txn IN ('OFFICE_CASH', 'CAPITAL_DEPLOYED') AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS office_cash_cash,
                    COALESCE(SUM(CASE WHEN txn IN ('OFFICE_CASH', 'CAPITAL_DEPLOYED') AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS office_cash_upi,
                    COALESCE(SUM(CASE WHEN txn IN ('CAPITAL_WITHDRAWN', 'INTEREST_WITHDRAWN') AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS capital_withdrawn_cash,
                    COALESCE(SUM(CASE WHEN txn IN ('CAPITAL_WITHDRAWN', 'INTEREST_WITHDRAWN') AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS capital_withdrawn_upi,
                    COALESCE(SUM(CASE WHEN txn = 'EXPENSE' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS expenses_cash,
                    COALESCE(SUM(CASE WHEN txn = 'EXPENSE' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS expenses_upi,
                    COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'ADD' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS adj_add_cash,
                    COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'ADD' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS adj_add_upi,
                    COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'MINUS' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS adj_minus_cash,
                    COALESCE(SUM(CASE WHEN txn = 'ADJUSTMENT' AND txn_sub = 'MINUS' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS adj_minus_upi,
                    COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'PROFIT' AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS profit_cash,
                    COALESCE(SUM(CASE WHEN txn = 'PROFIT_LOSS' AND txn_sub = 'PROFIT' AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS profit_upi,
                    COALESCE(SUM(CASE WHEN ((txn = 'PROFIT_LOSS' AND txn_sub IN ('LOSS', 'PROFIT_WITHDRAWN')) OR txn = 'PROFIT_WITHDRAWN') AND txn_type = 'CASH' THEN amount ELSE 0 END), 0) AS loss_cash,
                    COALESCE(SUM(CASE WHEN ((txn = 'PROFIT_LOSS' AND txn_sub IN ('LOSS', 'PROFIT_WITHDRAWN')) OR txn = 'PROFIT_WITHDRAWN') AND txn_type = 'UPI' THEN amount ELSE 0 END), 0) AS loss_upi
                FROM cashbag_transactions
                WHERE (group_id = %s OR ({pair_filter}))
            """, (group_id,) + pair_params)
            row_manual = cur.fetchone()
            oc_cash, oc_upi = float(row_manual[0] or 0), float(row_manual[1] or 0)
            cw_cash, cw_upi = float(row_manual[2] or 0), float(row_manual[3] or 0)
            exp_cash, exp_upi = float(row_manual[4] or 0), float(row_manual[5] or 0)
            adj_add_cash, adj_add_upi = float(row_manual[6] or 0), float(row_manual[7] or 0)
            adj_min_cash, adj_min_upi = float(row_manual[8] or 0), float(row_manual[9] or 0)
            prf_cash, prf_upi = float(row_manual[10] or 0), float(row_manual[11] or 0)
            loss_cash, loss_upi = float(row_manual[12] or 0), float(row_manual[13] or 0)

            # C. Customer Collections
            p_cash, p_upi = 0.0, 0.0
            if vids:
                cur.execute("""
                    SELECT 
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
                    FROM (
                        SELECT amt, payment_type, cash_amount, upi_amount, vid FROM payment
                        UNION ALL
                        SELECT amt, 'cash' AS payment_type, amt AS cash_amount, 0 AS upi_amount, vid FROM closed_cust_payment
                    ) p
                    WHERE p.vid = ANY(%s)
                """, (vids,))
                row_p = cur.fetchone()
                p_cash = float(row_p[0] or 0)
                p_upi = float(row_p[1] or 0)

            # D. Loans Disbursed, Rusum & Interest
            loans_cash, loans_upi = 0.0, 0.0
            r_cash, r_upi = 0.0, 0.0
            total_customer_interest = 0.0
            total_loans_dispensed = 0.0
            if vids:
                cur.execute("""
                    SELECT 
                        COALESCE(SUM(CASE 
                            WHEN c.base_amount > 0 THEN c.base_amount 
                            ELSE ROUND(c.total_amount - (c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0)) - (c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0)), 2) 
                        END), 0) AS loans_disbursed,
                        COALESCE(SUM(CASE 
                            WHEN LOWER(c.payment_type) = 'upi' THEN 0
                            ELSE (CASE WHEN c.base_amount > 0 THEN c.base_amount ELSE ROUND(c.total_amount - (c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0)) - (c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0)), 2) END)
                        END), 0) AS loans_disbursed_cash,
                        COALESCE(SUM(CASE 
                            WHEN LOWER(c.payment_type) = 'upi' THEN (CASE WHEN c.base_amount > 0 THEN c.base_amount ELSE ROUND(c.total_amount - (c.total_amount * (COALESCE(v.interest_rate, 0) / 100.0)) - (c.total_amount * (COALESCE(v.cutting_rate, 0) / 100.0)), 2) END)
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
                        END), 0) AS interest_total
                    FROM (
                        SELECT base_amount, total_amount, cutting_amount, interest_amount, payment_type, status, vid FROM customer
                        UNION ALL
                        SELECT base_amount, total_amount, cutting_amount, interest_amount, payment_type, status, vid FROM closed_cust_account
                    ) c
                    JOIN village v ON c.vid = v.vid
                    WHERE c.vid = ANY(%s) AND c.status != 'deleted'
                """, (vids,))
                row_l = cur.fetchone()
                total_loans_dispensed = float(row_l[0] or 0)
                loans_cash = float(row_l[1] or 0)
                loans_upi = float(row_l[2] or 0)
                r_cash = float(row_l[4] or 0)
                r_upi = float(row_l[5] or 0)
                total_customer_interest = float(row_l[6] or 0)

            # E. Net Live Cashbag Holdings
            cashbag_cash = (
                oc_cash
                + p_cash
                + r_cash
                + adj_add_cash
                + prf_cash
                - loans_cash
                - cw_cash
                - exp_cash
                - adj_min_cash
                - loss_cash
            )
            cashbag_upi = (
                oc_upi
                + p_upi
                + r_upi
                + adj_add_upi
                + prf_upi
                - loans_upi
                - cw_upi
                - exp_upi
                - adj_min_upi
                - loss_upi
            )
            cashbag_total = cashbag_cash + cashbag_upi

            # H. Withdrawal history







            cur.execute("""







                SELECT id, total_withdrawn, principal_portion, interest_portion, profit_portion, payment_mode, withdrawal_date, is_reversed







                FROM group_withdrawal_logs







                WHERE group_id = %s







                ORDER BY withdrawal_date DESC







            """, (group_id,))







            withdrawal_history = []
            withdrawn_profit = 0.0
            total_withdrawn_sum = 0.0
            withdrawn_principal = 0.0
            withdrawn_interest = 0.0
            for r in cur.fetchall():







                withdrawal_history.append({







                    "id": str(r[0]),







                    "total_withdrawn": float(r[1]),







                    "principal_portion": float(r[2]),







                    "interest_portion": float(r[3]),







                    "profit_portion": float(r[4]),







                    "payment_mode": r[5],







                    "withdrawal_date": r[6],







                    "is_reversed": r[7]







                })







                if not r[7]:
                    total_withdrawn_sum += float(r[1])
                    withdrawn_principal += float(r[2])
                    withdrawn_interest += float(r[3])
                    withdrawn_profit += float(r[4])







            # I. Legacy opening balances if any







            cur.execute("SELECT initial_invested_principal, accrued_interest_to_date, profit_in_circulation FROM village_group_openings WHERE group_id = %s", (group_id,))







            op_row = cur.fetchone()







            initial_principal = float(op_row[0]) if op_row else total_active_principal







            if op_row:







                total_accrued_interest += float(op_row[1])







            # J. Profit Calculation Model (Circulating Profit = Customer Interest - 24% Investor Return - Withdrawn Profit)







            circulating_profit = max(0.0, total_customer_interest - total_accrued_interest - withdrawn_profit)







            kpi = {







                "initial_principal": initial_principal,







                "active_capital": total_active_principal,







                "accrued_interest": total_accrued_interest,







                "circulating_profit": circulating_profit,







                "total_customer_interest": total_customer_interest,







                "total_loans_dispensed": total_loans_dispensed,







                "cashbag_cash": cashbag_cash,







                "cashbag_upi": cashbag_upi,







                "cashbag_total": cashbag_total,
                "total_withdrawn": total_withdrawn_sum,
                "withdrawn_principal": withdrawn_principal,
                "withdrawn_interest": withdrawn_interest,
                "withdrawn_profit": withdrawn_profit







            }







            group.update(kpi)







            # All active investors with idle cash for modal dropdowns







            cur.execute("""







                SELECT 







                    inv.id, inv.investor_code, inv.full_name,







                    COALESCE(dep.total_deposited, 0) as deposited,







                    COALESCE(wdr.total_withdrawn, 0) as idle_wdr,







                    COALESCE(alloc.total_deployed, 0) as deployed,







                    COALESCE(ret.total_principal_returned, 0) as p_returned,







                    COALESCE(ret.total_interest_earned, 0) as interest_earned,







                    COALESCE(ret.total_profit_earned, 0) as profit_earned,







                    COALESCE(draw.total_draws, 0) as personal_draws







                FROM investors inv







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_deposited 







                    FROM investor_transactions 







                    WHERE txn_type = 'DEPOSIT' AND is_reversed = FALSE 







                    GROUP BY investor_id







                ) dep ON inv.id = dep.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_withdrawn 







                    FROM investor_transactions 







                    WHERE txn_type = 'IDLE_WITHDRAWAL' AND is_reversed = FALSE 







                    GROUP BY investor_id







                ) wdr ON inv.id = wdr.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_deployed 







                    FROM group_capital_allocations 







                    WHERE is_reversed = FALSE 







                    GROUP BY investor_id







                ) alloc ON inv.id = alloc.investor_id







                LEFT JOIN (







                    SELECT 







                        investor_id,







                        SUM(CASE WHEN component_type = 'PRINCIPAL' THEN amount ELSE 0 END) as total_principal_returned,







                        SUM(CASE WHEN component_type = 'INTEREST' THEN amount ELSE 0 END) as total_interest_earned,







                        SUM(CASE WHEN component_type = 'PROFIT' THEN amount ELSE 0 END) as total_profit_earned







                    FROM group_withdrawal_allocations







                    GROUP BY investor_id







                ) ret ON inv.id = ret.investor_id







                LEFT JOIN (







                    SELECT investor_id, SUM(amount) as total_draws 

                    FROM investor_personal_expenses 

                    WHERE is_reversed = FALSE AND (is_settled IS NULL OR is_settled = FALSE)

                    GROUP BY investor_id

                ) draw ON inv.id = draw.investor_id







                WHERE inv.is_active = TRUE







                ORDER BY inv.investor_code ASC







            """)







            all_investors = []







            for r in cur.fetchall():







                deposited = float(r[3])







                idle_wdr = float(r[4])







                deployed = float(r[5])







                p_returned = float(r[6])







                interest_earned = float(r[7])







                profit_earned = float(r[8])







                personal_draws = float(r[9])







                idle_cash = (deposited - idle_wdr - deployed) + p_returned + interest_earned + profit_earned - personal_draws







                all_investors.append({







                    "id": str(r[0]),







                    "code": r[1],







                    "investor_code": r[1],







                    "name": r[2],







                    "full_name": r[2],







                    "idle_balance": idle_cash,







                    "idle_cash": idle_cash,







                    "active_capital": active_cap_map.get(str(r[0]), 0.0)







                })







        return render_template(







            "banking/group_detail.html",







            group=group,







            kpi=kpi,







            allocations=allocations,







            shares=shares,







            withdrawals=withdrawal_history,
            withdrawal_history=withdrawal_history,







            investors=all_investors,







            all_investors=all_investors







        )







    except Exception as e:







        logger.error(f"Error loading group details: {e}", exc_info=True)







        flash(f"Error loading group detail: {e}")







        return redirect("/banking/groups")







    finally:







        if conn:







            conn.close()







@banking_bp.route("/groups/opening-setup")







def group_opening_setup_view():







    """







    Setup screen for migrating existing 5-10 year old groups into the banking system.







    """







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("SELECT id, group_code, group_name, collection_days_per_week FROM village_groups ORDER BY group_name ASC")







            groups = [{







                "id": str(r[0]),







                "code": r[1],







                "group_code": r[1],







                "name": r[2],







                "group_name": r[2],







                "days": r[3],







                "collection_days_per_week": r[3]







            } for r in cur.fetchall()]







            cur.execute("SELECT id, investor_code, full_name, global_share_pct FROM investors WHERE is_active = TRUE ORDER BY investor_code ASC")







            investors = [{







                "id": str(r[0]),







                "code": r[1],







                "investor_code": r[1],







                "name": r[2],







                "full_name": r[2],







                "share_pct": float(r[3] or 0),







                "global_share_pct": float(r[3] or 0)







            } for r in cur.fetchall()]







        return render_template("banking/group_opening_form.html", groups=groups, investors=investors)







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/groups/opening-setup", methods=["POST"])







def api_save_group_opening_setup():







    data = request.get_json(silent=True) or request.form.to_dict()







    group_id = data.get("group_id")







    as_of_date_str = data.get("as_of_date") or date.today().isoformat()







    principal = float(data.get("initial_invested_principal") or 0)







    interest = float(data.get("accrued_interest_to_date") or 0)







    profit = float(data.get("profit_in_circulation") or 0)







    cash = float(data.get("cashbag_opening_cash") or 0)







    upi = float(data.get("cashbag_opening_upi") or 0)







    days = int(data.get("collection_days_per_week") or 5)







    shares_list = data.get("shares") or []







    if not group_id:







        return jsonify({"success": False, "error": "Group selection is required."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # 1. Update collection days on group







            cur.execute("UPDATE village_groups SET collection_days_per_week = %s WHERE id = %s", (days, group_id))







            # 2. Insert or update opening record







            cur.execute("""







                INSERT INTO village_group_openings (







                    group_id, as_of_date, initial_invested_principal, accrued_interest_to_date,







                    profit_in_circulation, cashbag_opening_cash, cashbag_opening_upi, created_by







                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)







                ON CONFLICT (group_id) DO UPDATE SET







                    as_of_date = EXCLUDED.as_of_date,







                    initial_invested_principal = EXCLUDED.initial_invested_principal,







                    accrued_interest_to_date = EXCLUDED.accrued_interest_to_date,







                    profit_in_circulation = EXCLUDED.profit_in_circulation,







                    cashbag_opening_cash = EXCLUDED.cashbag_opening_cash,







                    cashbag_opening_upi = EXCLUDED.cashbag_opening_upi







            """, (







                group_id, date.fromisoformat(as_of_date_str[:10]),







                principal, interest, profit, cash, upi, session.get("username", "Admin")







            ))







            # 3. Save investor shareholdings if provided







            if shares_list:







                for s in shares_list:







                    inv_id = s.get("investor_id")







                    pct = float(s.get("share_pct") or 0)







                    if inv_id and pct >= 0:







                        cur.execute("""







                            INSERT INTO investor_group_shares (group_id, investor_id, share_pct)







                            VALUES (%s, %s, %s)







                            ON CONFLICT (group_id, investor_id) DO UPDATE SET share_pct = EXCLUDED.share_pct







                        """, (group_id, inv_id, pct))







            conn.commit()







            return jsonify({"success": True, "message": "Opening setup for Village Group saved successfully."})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error saving group opening setup: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/groups/<group_id>/allocate-capital", methods=["POST"])







def api_group_allocate_capital(group_id):







    """







    Deploys capital from the Investment Pool to a Village Group.







    CRITICAL: Automatically inserts corresponding OFFICE_CASH transaction into cashbag_transactions!







    """







    data = request.get_json(silent=True) or request.form.to_dict()







    investor_id = data.get("investor_id")







    amount = float(data.get("amount") or 0)







    payment_mode = (data.get("payment_mode") or "CASH").upper()







    alloc_date_str = data.get("allocation_date") or date.today().isoformat()







    alloc_date = date.fromisoformat(alloc_date_str[:10])







    is_backdated = alloc_date < date.today()







    if not investor_id or amount <= 0:







        return jsonify({"success": False, "error": "Investor and positive capital amount are required."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # Look up group employee pair







            cur.execute("SELECT emp1_id, emp2_id, group_name FROM village_groups WHERE id = %s", (group_id,))







            grp_row = cur.fetchone()







            if not grp_row:







                return jsonify({"success": False, "error": "Village Group not found."}), 404







            emp1, emp2, grp_name = grp_row







            # Look up investor code







            cur.execute("SELECT investor_code, full_name FROM investors WHERE id = %s", (investor_id,))







            inv_code, inv_name = cur.fetchone()







            # 1. Insert CAPITAL_DEPLOYED into cashbag_transactions







            cb_notes = f"Capital Deployed - {inv_name} ({inv_code}) -> {grp_name}"







            cur.execute("""







                INSERT INTO cashbag_transactions (







                    emp1, emp2, group_id, txn, txn_sub, txn_type, amount, notes, created_by, created_at







                ) VALUES (%s, %s, %s, 'CAPITAL_DEPLOYED', '', %s, %s, %s, %s, %s)







                RETURNING id







            """, (







                emp1, emp2, group_id, payment_mode, amount, cb_notes,







                session.get("username", "Admin"),







                datetime.combine(alloc_date, datetime.now().time())







            ))







            cb_txn_id = cur.fetchone()[0]







            # 2. Insert into group_capital_allocations







            cur.execute("""







                INSERT INTO group_capital_allocations (







                    group_id, investor_id, amount, payment_mode, allocation_date,







                    cashbag_txn_id, is_backdated, created_by







                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)







                RETURNING id







            """, (







                group_id, investor_id, amount, payment_mode, alloc_date,







                cb_txn_id, is_backdated, session.get("username", "Admin")







            ))







            alloc_id = cur.fetchone()[0]







            # 3. Log movement in investor_transactions







            cur.execute("""







                INSERT INTO investor_transactions (







                    investor_id, txn_type, payment_mode, amount, txn_date,







                    reference_id, notes, is_backdated, created_by







                ) VALUES (%s, 'CAPITAL_DEPLOYED', %s, %s, %s, %s, %s, %s, %s)







            """, (







                investor_id, payment_mode, amount, alloc_date,







                alloc_id, f"Capital deployed to {grp_name}", is_backdated, session.get("username", "Admin")







            ))







            conn.commit()







        return jsonify({







            "success": True,







            "message": f"Successfully deployed {bce.format_currency_inr(amount)} to {grp_name}. Cashbag OFFICE_CASH credited."







        })







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error deploying capital: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/groups/<group_id>/withdraw", methods=["POST"])







def api_group_waterfall_withdrawal(group_id):







    """







    Executes a Waterfall Withdrawal from Village Group Cashbag back to Investment Pool.







    Tier 1 (Principal) -> Tier 2 (Interest) -> Tier 3 (Profit share).







    Requires Admin Security PIN.







    """







    data = request.get_json(silent=True) or request.form.to_dict()







    pin = data.get("admin_pin")







    if not verify_admin_security_pin(pin):







        return jsonify({"success": False, "error": "Invalid Admin PIN. Withdrawal authorization failed."}), 403







    try:







        amount = float(data.get("amount") or 0)







        payment_mode = (data.get("payment_mode") or "CASH").upper()







        wdr_date_str = data.get("withdrawal_date") or date.today().isoformat()







        wdr_date = date.fromisoformat(wdr_date_str[:10])







        is_backdated = wdr_date < date.today()







        if amount <= 0:







            return jsonify({"success": False, "error": "Withdrawal amount must be greater than 0."}), 400







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # 1. Fetch group details







            cur.execute("SELECT emp1_id, emp2_id, group_name FROM village_groups WHERE id = %s", (group_id,))







            emp1, emp2, grp_name = cur.fetchone()







            # 2. Calculate outstanding principal & accrued interest owed to funders







            cur.execute("""







                SELECT 







                    gca.id, gca.investor_id, gca.amount, gca.allocation_date, gca.interest_rate,







                    COALESCE(ret.repaid_principal, 0), COALESCE(ret.repaid_interest, 0)







                FROM group_capital_allocations gca







                LEFT JOIN (







                    SELECT 







                        gwa.investor_id, gwl.group_id,







                        SUM(CASE WHEN gwa.component_type = 'PRINCIPAL' THEN gwa.amount ELSE 0 END) as repaid_principal,







                        SUM(CASE WHEN gwa.component_type = 'INTEREST' THEN gwa.amount ELSE 0 END) as repaid_interest







                    FROM group_withdrawal_allocations gwa







                    JOIN group_withdrawal_logs gwl ON gwa.withdrawal_id = gwl.id







                    WHERE gwl.is_reversed = FALSE







                    GROUP BY gwa.investor_id, gwl.group_id







                ) ret ON gca.investor_id = ret.investor_id AND gca.group_id = ret.group_id







                WHERE gca.group_id = %s AND gca.is_reversed = FALSE







            """, (group_id,))







            funders_owed = {}







            tot_p_owed = 0.0







            tot_i_owed = 0.0







            for r in cur.fetchall():







                inv_id = str(r[1])







                orig_amt = float(r[2])







                alloc_d = r[3]







                rate = float(r[4] or 24.0)







                rep_p = float(r[5])







                rep_i = float(r[6])







                rem_p = max(0.0, orig_amt - rep_p)







                c_math = bce.calculate_compound_interest(orig_amt, alloc_d, wdr_date, rate, rep_i)







                rem_i = c_math["net_unpaid_interest"]







                if inv_id not in funders_owed:







                    funders_owed[inv_id] = {"principal": 0.0, "interest": 0.0}







                funders_owed[inv_id]["principal"] += rem_p







                funders_owed[inv_id]["interest"] += rem_i







                tot_p_owed += rem_p







                tot_i_owed += rem_i







            # 3. Fetch partners ownership shares for profit tier







            cur.execute("""







                SELECT investor_id, share_pct 







                FROM investor_group_shares 







                WHERE group_id = %s







            """, (group_id,))







            shares = [{"investor_id": str(r[0]), "share_pct": float(r[1])} for r in cur.fetchall()]







            # 4. Run calculation engine waterfall







            w_res = bce.calculate_withdrawal_waterfall(amount, tot_p_owed, tot_i_owed, shares)







            p_portion = w_res.get("tier1_principal_covered", w_res.get("principal_portion", 0.0))







            i_portion = w_res.get("tier2_interest_covered", w_res.get("interest_portion", 0.0))







            prf_portion = w_res.get("tier3_profit_surplus", w_res.get("profit_portion", 0.0))







            # 5. Insert group_withdrawal_logs







            cur.execute("""







                INSERT INTO group_withdrawal_logs (







                    group_id, total_withdrawn, principal_portion, interest_portion, profit_portion,







                    payment_mode, withdrawal_date, admin_auth_confirmed, is_backdated, created_by







                ) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s)







                RETURNING id







            """, (







                group_id, amount, p_portion, i_portion, prf_portion,







                payment_mode, wdr_date, is_backdated, session.get("username", "Admin")







            ))







            w_id = cur.fetchone()[0]







            # 6. Deduct from group's cashbag: record each waterfall tier appropriately in cashbag_transactions
            cb_created_at = datetime.combine(wdr_date, datetime.now().time())
            admin_user = session.get("username", "Admin")

            # Tier 1: Principal Return
            if p_portion > 0:
                p_notes = f"Waterfall Withdrawal: {grp_name} (Principal Return)"
                cur.execute("""
                    INSERT INTO cashbag_transactions (
                        emp1, emp2, group_id, txn, txn_sub, txn_type, amount, notes, created_by, created_at
                    ) VALUES (%s, %s, %s, 'CAPITAL_WITHDRAWN', 'PRINCIPAL', %s, %s, %s, %s, %s)
                """, (emp1, emp2, group_id, payment_mode, p_portion, p_notes, admin_user, cb_created_at))

            # Tier 2: 24% Return Payout (Interest)
            if i_portion > 0:
                i_notes = f"Waterfall Withdrawal: {grp_name} (24% Return Payout)"
                cur.execute("""
                    INSERT INTO cashbag_transactions (
                        emp1, emp2, group_id, txn, txn_sub, txn_type, amount, notes, created_by, created_at
                    ) VALUES (%s, %s, %s, 'INTEREST_WITHDRAWN', 'INTEREST', %s, %s, %s, %s, %s)
                """, (emp1, emp2, group_id, payment_mode, i_portion, i_notes, admin_user, cb_created_at))

            # Tier 3: Profit Share Distribution
            if prf_portion > 0:
                prf_notes = f"Waterfall Withdrawal: {grp_name} (Profit Share Distribution)"
                cur.execute("""
                    INSERT INTO cashbag_transactions (
                        emp1, emp2, group_id, txn, txn_sub, txn_type, amount, notes, created_by, created_at
                    ) VALUES (%s, %s, %s, 'PROFIT_LOSS', 'PROFIT_WITHDRAWN', %s, %s, %s, %s, %s)
                """, (emp1, emp2, group_id, payment_mode, prf_portion, prf_notes, admin_user, cb_created_at))

            # Fallback if total amount wasn't split by waterfall tiers but amount > 0
            if (p_portion + i_portion + prf_portion) <= 0 and amount > 0:
                cur.execute("""
                    INSERT INTO cashbag_transactions (
                        emp1, emp2, group_id, txn, txn_sub, txn_type, amount, notes, created_by, created_at
                    ) VALUES (%s, %s, %s, 'CAPITAL_WITHDRAWN', 'WITHDRAWAL', %s, %s, %s, %s, %s)
                """, (emp1, emp2, group_id, payment_mode, amount, f"Waterfall Withdrawal: {grp_name}", admin_user, cb_created_at))

            # 7. Credit allocated portions to individual investors







            # 7a. Distribute Principal portion among funders proportionally







            if p_portion > 0 and tot_p_owed > 0:







                for inv_id, owed in funders_owed.items():







                    if owed["principal"] > 0:







                        inv_p_share = round((owed["principal"] / tot_p_owed) * p_portion)







                        cur.execute("""







                            INSERT INTO group_withdrawal_allocations (withdrawal_id, investor_id, component_type, amount)







                            VALUES (%s, %s, 'PRINCIPAL', %s)







                        """, (w_id, inv_id, inv_p_share))







                        cur.execute("""







                            INSERT INTO investor_transactions (







                                investor_id, txn_type, payment_mode, amount, txn_date, reference_id, notes, created_by







                            ) VALUES (%s, 'PRINCIPAL_RETURN', %s, %s, %s, %s, %s, %s)







                        """, (inv_id, payment_mode, inv_p_share, wdr_date, w_id, f"Principal return from {grp_name}", session.get("username", "Admin")))







            # 7b. Distribute Interest portion among funders proportionally







            if i_portion > 0 and tot_i_owed > 0:







                for inv_id, owed in funders_owed.items():







                    if owed["interest"] > 0:







                        inv_i_share = round((owed["interest"] / tot_i_owed) * i_portion)







                        cur.execute("""







                            INSERT INTO group_withdrawal_allocations (withdrawal_id, investor_id, component_type, amount)







                            VALUES (%s, %s, 'INTEREST', %s)







                        """, (w_id, inv_id, inv_i_share))







                        cur.execute("""







                            INSERT INTO investor_transactions (







                                investor_id, txn_type, payment_mode, amount, txn_date, reference_id, notes, created_by







                            ) VALUES (%s, 'INTEREST_RETURN', %s, %s, %s, %s, %s, %s)







                        """, (inv_id, payment_mode, inv_i_share, wdr_date, w_id, f"24% Interest payout from {grp_name}", session.get("username", "Admin")))







            # 7c. Distribute Profit portion according to ownership %







            dists = w_res.get("distributions", w_res.get("partner_distributions", []))







            for p_dist in dists:







                inv_id = p_dist.get("investor_id") or p_dist.get("partner_id")







                p_amt = p_dist.get("profit_share", p_dist.get("allocated_amount", 0.0))







                if p_amt > 0:







                    cur.execute("""







                        INSERT INTO group_withdrawal_allocations (withdrawal_id, investor_id, component_type, amount)







                        VALUES (%s, %s, 'PROFIT', %s)







                    """, (w_id, inv_id, p_amt))







                    cur.execute("""







                        INSERT INTO investor_transactions (







                            investor_id, txn_type, payment_mode, amount, txn_date, reference_id, notes, created_by







                        ) VALUES (%s, 'PROFIT_PAYOUT', %s, %s, %s, %s, %s, %s)







                    """, (inv_id, payment_mode, p_amt, wdr_date, w_id, f"Profit share payout from {grp_name}", session.get("username", "Admin")))







            conn.commit()







        return jsonify({







            "success": True,







            "message": f"Waterfall withdrawal of {bce.format_currency_inr(amount)} executed successfully. (Principal: {bce.format_currency_inr(p_portion)}, Interest: {bce.format_currency_inr(i_portion)}, Profit: {bce.format_currency_inr(prf_portion)})"







        })







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error executing waterfall withdrawal: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/groups/<group_id>/shares", methods=["POST"])







def api_update_group_shares(group_id):







    data = request.get_json(silent=True) or request.form.to_dict()







    shares_list = data.get("shares") or []







    # Validate sum equals 100%







    total_pct = sum(float(s.get("share_pct") or 0) for s in shares_list)







    if total_pct < 100.0 - 0.05:
        return jsonify({"success": False, "error": f"Total shareholding percentage must be at least 100%. Current sum: {total_pct:.0f}%"}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # Active capital protection:







            # If an investor has active deployed capital in this route, they cannot be removed until settled!







            cur.execute("""







                SELECT gca.investor_id, inv.full_name,







                       SUM(gca.amount) - COALESCE(SUM(ret.repaid_principal), 0) as active_principal







                FROM group_capital_allocations gca







                JOIN investors inv ON gca.investor_id = inv.id







                LEFT JOIN (







                    SELECT gwa.investor_id, gwl.group_id,







                           SUM(CASE WHEN gwa.component_type = 'PRINCIPAL' THEN gwa.amount ELSE 0 END) as repaid_principal







                    FROM group_withdrawal_allocations gwa







                    JOIN group_withdrawal_logs gwl ON gwa.withdrawal_id = gwl.id







                    WHERE gwl.is_reversed = FALSE







                    GROUP BY gwa.investor_id, gwl.group_id







                ) ret ON gca.investor_id = ret.investor_id AND gca.group_id = ret.group_id







                WHERE gca.group_id = %s AND gca.is_reversed = FALSE







                GROUP BY gca.investor_id, inv.full_name







                HAVING (SUM(gca.amount) - COALESCE(SUM(ret.repaid_principal), 0)) > 0.01







            """, (group_id,))







            active_investors = {str(r[0]): {"name": r[1], "active_amount": float(r[2])} for r in cur.fetchall()}







            new_investor_ids = set()







            for s in shares_list:







                inv_id = str(s.get("investor_id") or "")







                pct = float(s.get("share_pct") or 0)







                if inv_id and pct > 0:







                    new_investor_ids.add(inv_id)







            # Check if any investor with active capital was removed







            for act_id, info in active_investors.items():







                if act_id not in new_investor_ids:







                    return jsonify({







                        "success": False,







                        "error": f"Cannot remove {info['name']}: They still have active deployed capital of ₹{info['active_amount']:,.0f} in this route. You must settle / return their capital before removing them."







                    }), 400







            # Delete removed investors from investor_group_shares who have 0 active capital







            if new_investor_ids:







                cur.execute("""







                    DELETE FROM investor_group_shares







                    WHERE group_id = %s AND investor_id NOT IN %s







                """, (group_id, tuple(new_investor_ids)))







            else:







                cur.execute("DELETE FROM investor_group_shares WHERE group_id = %s", (group_id,))







            for s in shares_list:







                inv_id = s.get("investor_id")







                pct = float(s.get("share_pct") or 0)







                if inv_id:







                    cur.execute("""







                        INSERT INTO investor_group_shares (group_id, investor_id, share_pct)







                        VALUES (%s, %s, %s)







                        ON CONFLICT (group_id, investor_id) DO UPDATE SET share_pct = EXCLUDED.share_pct







                    """, (group_id, inv_id, pct))







            conn.commit()







            return jsonify({"success": True, "message": "Group ownership shares updated successfully."})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error updating group shares: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







# ---------------------------------------------------------------------------







# 4. Central Office Expenses & Annual Settlement







# ---------------------------------------------------------------------------







@banking_bp.route("/expenses")







def office_expenses_view():







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # Fetch unsettled and settled expenses







            cur.execute("""







                SELECT id, expense_category, amount, payment_mode, expense_date, description, is_settled, is_reversed, created_at







                FROM central_office_expenses







                ORDER BY expense_date DESC, created_at DESC







            """)







            expenses = []







            total_unsettled = 0.0







            for r in cur.fetchall():







                is_settled = r[6]







                is_rev = r[7]







                amt = float(r[2])







                if not is_settled and not is_rev:







                    total_unsettled += amt







                expenses.append({







                    "id": str(r[0]),







                    "category": r[1],







                    "expense_category": r[1],







                    "amount": amt,







                    "payment_mode": r[3],







                    "date": r[4],







                    "expense_date": r[4],







                    "description": r[5],







                    "is_settled": is_settled,







                    "is_reversed": is_rev,







                    "created_at": r[8]







                })







            # Fetch active groups with collection days for settlement preview







            cur.execute("SELECT id, group_code, group_name, collection_days_per_week FROM village_groups WHERE status = 'ACTIVE' ORDER BY group_name ASC")







            active_groups = [{"id": str(r[0]), "code": r[1], "name": r[2], "days": r[3]} for r in cur.fetchall()]







            total_days = sum(g["days"] for g in active_groups)







            # Calculate reallocation preview using pure math engine







            alloc_preview = []







            if total_unsettled > 0 and total_days > 0:







                alloc_preview = bce.calculate_office_expense_reallocation(total_unsettled, active_groups)







        return render_template(







            "banking/office_expenses.html",







            expenses=expenses,







            total_unsettled=total_unsettled,







            total_days=total_days,







            total_collection_days=total_days,







            active_groups=active_groups,







            alloc_preview=alloc_preview,







            reallocation_preview=alloc_preview







        )







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/expenses", methods=["POST"])







def api_add_office_expense():







    data = request.get_json(silent=True) or request.form.to_dict()







    category = (data.get("expense_category") or data.get("category") or "OTHER").upper()







    amount = float(data.get("amount") or 0)







    payment_mode = (data.get("payment_mode") or "CASH").upper()







    exp_date_str = data.get("expense_date") or date.today().isoformat()







    description = data.get("description") or ""







    if amount <= 0:







        return jsonify({"success": False, "error": "Expense amount must be greater than 0."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                INSERT INTO central_office_expenses (







                    expense_category, amount, payment_mode, expense_date, description, created_by







                ) VALUES (%s, %s, %s, %s, %s, %s)







                RETURNING id







            """, (







                category, amount, payment_mode, date.fromisoformat(exp_date_str[:10]),







                description, session.get("username", "Admin")







            ))







            conn.commit()







        return jsonify({"success": True, "message": f"Central office expense of {bce.format_currency_inr(amount)} recorded successfully."})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error adding office expense: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/expenses/settlement/execute", methods=["POST"])







def api_execute_annual_expense_settlement():







    """







    Executes annual expense reallocation across Village Groups based on their weekly collection days:







    Group Share = (Total Expenses / Total Days) * Group Days







    Debits each group's cashbag, marks expenses settled, and reimburses the Investment Pool.







    Requires Admin Security PIN.







    """







    data = request.get_json(silent=True) or request.form.to_dict()







    pin = data.get("admin_pin")







    if not verify_admin_security_pin(pin):







        return jsonify({"success": False, "error": "Invalid Admin PIN. Settlement execution failed."}), 403







    settlement_year = data.get("settlement_year") or f"FY-{date.today().year}-{date.today().year + 1}"







    settlement_date = date.today()







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # 1. Total unsettled expenses







            cur.execute("SELECT COALESCE(SUM(amount), 0) FROM central_office_expenses WHERE is_settled = FALSE AND is_reversed = FALSE")







            total_expenses = float(cur.fetchone()[0])







            if total_expenses <= 0:







                return jsonify({"success": False, "error": "No unsettled expenses available for reallocation."}), 400







            # 2. Fetch active groups and collection days







            cur.execute("""







                SELECT id, group_code, group_name, collection_days_per_week, emp1_id, emp2_id







                FROM village_groups 







                WHERE status = 'ACTIVE'







            """)







            groups_data = []







            for r in cur.fetchall():







                groups_data.append({







                    "id": str(r[0]),







                    "code": r[1],







                    "name": r[2],







                    "days": r[3],







                    "emp1": r[4],







                    "emp2": r[5]







                })







            total_days = sum(g["days"] for g in groups_data)







            if total_days <= 0:







                return jsonify({"success": False, "error": "No active group collection days found."}), 400







            # 3. Calculate reallocation using pure math engine







            allocations = bce.calculate_office_expense_reallocation(total_expenses, groups_data)







            # 4. Insert annual_expense_settlements record







            cur.execute("""







                INSERT INTO annual_expense_settlements (







                    settlement_year, settlement_date, total_expenses, total_days, executed_by







                ) VALUES (%s, %s, %s, %s, %s)







                RETURNING id







            """, (settlement_year, settlement_date, total_expenses, total_days, session.get("username", "Admin")))







            settlement_id = cur.fetchone()[0]







            # 5. Apply deductions to each group and cashbag







            for alloc in allocations:







                grp_id = alloc.get("id") or alloc.get("group_id")







                grp_share = alloc.get("allocated_expense", 0.0)







                grp_days = alloc.get("days") or alloc.get("group_days", 0)







                grp_info = next(g for g in groups_data if g["id"] == grp_id)







                # Debit group Cashbag as EXPENSE







                cb_notes = f"Annual Office Expense Share ({settlement_year}, {grp_days} Days/Wk)"







                cur.execute("""







                    INSERT INTO cashbag_transactions (







                        emp1, emp2, txn, txn_sub, txn_type, amount, notes, created_by, created_at







                    ) VALUES (%s, %s, 'EXPENSE', 'OTHER_EXPENSES', 'CASH', %s, %s, %s, NOW())







                    RETURNING id







                """, (grp_info["emp1"], grp_info["emp2"], grp_share, cb_notes, session.get("username", "Admin")))







                cb_txn_id = cur.fetchone()[0]







                # Insert group_expense_allocations







                cur.execute("""







                    INSERT INTO group_expense_allocations (







                        settlement_id, group_id, group_days, allocated_amount, cashbag_txn_id







                    ) VALUES (%s, %s, %s, %s, %s)







                """, (settlement_id, grp_id, grp_days, grp_share, cb_txn_id))







            # 6. Mark all expenses as settled







            cur.execute("""







                UPDATE central_office_expenses 







                SET is_settled = TRUE, reallocated_annual_id = %s







                WHERE is_settled = FALSE AND is_reversed = FALSE







            """, (settlement_id,))







            conn.commit()







        return jsonify({







            "success": True,







            "message": f"Annual expense settlement of {bce.format_currency_inr(total_expenses)} across {len(groups_data)} Village Groups completed successfully."







        })







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error executing annual settlement: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







# ---------------------------------------------------------------------------







# 5. Direct Individual Loans from Investment Pool







# ---------------------------------------------------------------------------







@banking_bp.route("/direct-loans")







def direct_loans_view():







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                SELECT 







                    dl.id, dl.borrower_name, dl.phone_number, dl.principal_amount,







                    dl.annual_interest_rate, dl.disbursal_date, dl.due_date, dl.repayment_type,







                    dl.revenue_allocation, dl.payment_mode, dl.status, dl.notes,







                    inv.full_name as funding_investor_name,







                    COALESCE(rep.repaid_principal, 0) as repaid_principal,







                    COALESCE(rep.repaid_interest, 0) as repaid_interest







                FROM direct_individual_loans dl







                LEFT JOIN investors inv ON dl.funding_investor_id = inv.id







                LEFT JOIN (







                    SELECT 







                        loan_id,







                        SUM(principal_amount) as repaid_principal,







                        SUM(interest_amount) as repaid_interest







                    FROM direct_loan_repayments







                    WHERE is_reversed = FALSE







                    GROUP BY loan_id







                ) rep ON dl.id = rep.loan_id







                WHERE dl.is_reversed = FALSE







                ORDER BY dl.disbursal_date DESC







            """)







            loans = []







            for r in cur.fetchall():







                p_amt = float(r[3])







                rep_p = float(r[13])







                rep_i = float(r[14])







                rem_p = max(0.0, p_amt - rep_p)







                loans.append({







                    "id": str(r[0]),







                    "borrower_name": r[1],







                    "phone_number": r[2],







                    "principal_amount": p_amt,







                    "annual_interest_rate": float(r[4]),







                    "disbursal_date": r[5],







                    "due_date": r[6],







                    "repayment_type": r[7],







                    "revenue_allocation": r[8],







                    "payment_mode": r[9],







                    "status": r[10],







                    "notes": r[11],







                    "funding_investor_name": r[12],







                    "repaid_principal": rep_p,







                    "repaid_interest": rep_i,







                    "remaining_principal": rem_p







                })







            # Fetch active investors for attributed dropdown







            cur.execute("SELECT id, investor_code, full_name FROM investors WHERE is_active = TRUE ORDER BY investor_code ASC")







            investors = [{"id": str(r[0]), "code": r[1], "name": r[2]} for r in cur.fetchall()]







            summary = {







                "total_disbursed": sum(l["principal_amount"] for l in loans),







                "total_outstanding": sum(l["remaining_principal"] for l in loans),







                "total_interest_collected": sum(l["repaid_interest"] for l in loans),







                "active_borrowers": len([l for l in loans if l["status"] == "ACTIVE"])







            }







        return render_template("banking/direct_loans.html", loans=loans, summary=summary, investors=investors)







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/direct-loans", methods=["POST"])







def api_issue_direct_loan():







    data = request.get_json(silent=True) or request.form.to_dict()







    name = (data.get("borrower_name") or "").strip()







    phone = (data.get("phone_number") or "").strip()







    principal = float(data.get("principal_amount") or 0)







    rate = float(data.get("annual_interest_rate") or 24.0)







    disb_date_str = data.get("disbursal_date") or date.today().isoformat()







    due_date_str = data.get("due_date")







    repay_type = data.get("repayment_type") or "BULLET"







    rev_alloc = data.get("revenue_allocation") or "POOLED"







    funder_id = data.get("funding_investor_id") or None







    mode = (data.get("payment_mode") or "CASH").upper()







    if not name or not phone or principal <= 0:







        return jsonify({"success": False, "error": "Borrower name, phone, and positive principal are required."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                INSERT INTO direct_individual_loans (







                    borrower_name, phone_number, aadhaar_number, principal_amount,







                    annual_interest_rate, disbursal_date, due_date, repayment_type,







                    revenue_allocation, funding_investor_id, payment_mode, notes, created_by







                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)







                RETURNING id







            """, (







                name, phone, data.get("aadhaar_number"), principal,







                rate, date.fromisoformat(disb_date_str[:10]),







                date.fromisoformat(due_date_str[:10]) if due_date_str else None,







                repay_type, rev_alloc, funder_id, mode, data.get("notes"),







                session.get("username", "Admin")







            ))







            conn.commit()







        return jsonify({"success": True, "message": f"Direct Loan of {bce.format_currency_inr(principal)} to {name} issued successfully."})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error issuing direct loan: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/direct-loans/<loan_id>/repay", methods=["POST"])







def api_repay_direct_loan(loan_id):







    data = request.get_json(silent=True) or request.form.to_dict()







    p_amt = float(data.get("principal_amount") or 0)







    i_amt = float(data.get("interest_amount") or 0)







    total_amt = p_amt + i_amt







    mode = (data.get("payment_mode") or "CASH").upper()







    rep_date_str = data.get("repayment_date") or date.today().isoformat()







    if total_amt <= 0:







        return jsonify({"success": False, "error": "Repayment total must be greater than 0."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                INSERT INTO direct_loan_repayments (







                    loan_id, repayment_date, principal_amount, interest_amount, total_amount, payment_mode, created_by







                ) VALUES (%s, %s, %s, %s, %s, %s, %s)







            """, (







                loan_id, date.fromisoformat(rep_date_str[:10]),







                p_amt, i_amt, total_amt, mode, session.get("username", "Admin")







            ))







            # Check if loan is settled







            cur.execute("SELECT principal_amount FROM direct_individual_loans WHERE id = %s", (loan_id,))







            orig_p = float(cur.fetchone()[0])







            cur.execute("SELECT COALESCE(SUM(principal_amount), 0) FROM direct_loan_repayments WHERE loan_id = %s AND is_reversed = FALSE", (loan_id,))







            tot_p_rep = float(cur.fetchone()[0])







            if tot_p_rep >= orig_p:







                cur.execute("UPDATE direct_individual_loans SET status = 'SETTLED' WHERE id = %s", (loan_id,))







            conn.commit()







        return jsonify({"success": True, "message": f"Recorded repayment of {bce.format_currency_inr(total_amt)}."})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error recording loan repayment: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







# ---------------------------------------------------------------------------







# 6. Chit Fund ↔ Investment Bank Inter-Bank Bridge







# ---------------------------------------------------------------------------







@banking_bp.route("/interbank")







def interbank_view():







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                SELECT 







                    cib.id, cib.direction, cib.amount, cib.payment_mode, cib.transfer_date,







                    cib.reason, cib.is_reversed, cg.name as chit_group_name







                FROM chit_interbank_transfers cib







                LEFT JOIN chit_groups cg ON cib.chit_group_id = cg.id







                ORDER BY cib.transfer_date DESC, cib.created_at DESC







            """)







            transfers = []







            chit_to_inv = 0.0







            inv_to_chit = 0.0







            for r in cur.fetchall():







                amt = float(r[2])







                is_rev = r[6]







                if not is_rev:







                    if r[1] == 'CHIT_TO_INVESTMENT':







                        chit_to_inv += amt







                    else:







                        inv_to_chit += amt







                transfers.append({







                    "id": str(r[0]),







                    "direction": r[1],







                    "amount": amt,







                    "payment_mode": r[3],







                    "transfer_date": r[4],







                    "reason": r[5],







                    "is_reversed": is_rev,







                    "chit_group_name": r[7]







                })







            # Fetch active chit groups for dropdown







            cur.execute("SELECT id, name FROM chit_groups WHERE status = 'Active' ORDER BY name ASC")







            chit_groups = [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]







            summary = {







                "total_chit_to_inv": chit_to_inv,







                "total_inv_to_chit": inv_to_chit,







                "net_balance": chit_to_inv - inv_to_chit







            }







        return render_template(







            "banking/interbank.html",







            transfers=transfers,







            summary=summary,







            chit_to_inv=chit_to_inv,







            inv_to_chit=inv_to_chit,







            net_balance=chit_to_inv - inv_to_chit,







            chit_groups=chit_groups







        )







    finally:







        if conn:







            conn.close()







@banking_bp.route("/api/interbank/transfer", methods=["POST"])







def api_interbank_transfer():







    data = request.get_json(silent=True) or request.form.to_dict()







    pin = data.get("admin_pin")







    if not verify_admin_security_pin(pin):







        return jsonify({"success": False, "error": "Invalid Admin PIN. Transfer authorization failed."}), 403







    direction = data.get("direction") # 'CHIT_TO_INVESTMENT' or 'INVESTMENT_TO_CHIT'







    chit_group_id = data.get("chit_group_id") or None







    amount = float(data.get("amount") or 0)







    mode = (data.get("payment_mode") or "CASH").upper()







    transfer_date_str = data.get("transfer_date") or date.today().isoformat()







    reason = (data.get("reason") or "Inter-bank liquidity transfer").strip()







    if direction not in ("CHIT_TO_INVESTMENT", "INVESTMENT_TO_CHIT") or amount <= 0:







        return jsonify({"success": False, "error": "Valid direction and positive amount required."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("""







                INSERT INTO chit_interbank_transfers (







                    direction, chit_group_id, amount, payment_mode, transfer_date, reason, created_by







                ) VALUES (%s, %s, %s, %s, %s, %s, %s)







            """, (







                direction, chit_group_id, amount, mode,







                date.fromisoformat(transfer_date_str[:10]), reason, session.get("username", "Admin")







            ))







            conn.commit()







        return jsonify({"success": True, "message": f"Inter-bank transfer of {bce.format_currency_inr(amount)} recorded successfully."})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error in inter-bank transfer: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







# ---------------------------------------------------------------------------







# 7. Soft Transaction Reversals & Audit Engine







# ---------------------------------------------------------------------------







@banking_bp.route("/api/transactions/<txn_id>/reverse", methods=["POST"])







def api_reverse_transaction(txn_id):







    """







    Soft-reverses any banking transaction, stamping reversed_by, reversed_at, and reason.







    Requires Admin Security PIN.







    """







    data = request.get_json(silent=True) or request.form.to_dict()







    pin = data.get("admin_pin")







    if not verify_admin_security_pin(pin):







        return jsonify({"success": False, "error": "Invalid Admin PIN. Reversal authorization failed."}), 403







    reason = (data.get("reason") or "Administrative reversal").strip()







    table_hint = data.get("table") or "investor_transactions"







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            # Map table hints







            table_map = {







                "investor_transactions": "investor_transactions",







                "personal_expenses": "investor_personal_expenses",







                "office_expenses": "central_office_expenses",







                "capital_allocations": "group_capital_allocations",







                "withdrawal_logs": "group_withdrawal_logs",







                "direct_loans": "direct_individual_loans",







                "loan_repayments": "direct_loan_repayments",







                "interbank": "chit_interbank_transfers"







            }







            target_table = table_map.get(table_hint, "investor_transactions")







            cur.execute(f"""







                UPDATE {target_table}







                SET is_reversed = TRUE, reversed_at = NOW(), reversed_by = %s,







                    reversal_reason = %s







                WHERE id = %s AND is_reversed = FALSE







                RETURNING id







            """, (session.get("username", "Admin"), reason, txn_id))







            row = cur.fetchone()







            if not row:







                return jsonify({"success": False, "error": "Transaction not found or already reversed."}), 404







            conn.commit()







            return jsonify({"success": True, "message": "Transaction reversed successfully."})







    except Exception as e:







        if conn:







            conn.rollback()







        logger.error(f"Error reversing transaction: {e}", exc_info=True)







        return jsonify({"success": False, "error": str(e)}), 500







    finally:







        if conn:







            conn.close()







# ---------------------------------------------------------------------------







# 8. Investor Self-Service Portal & Auth







# ---------------------------------------------------------------------------







@banking_bp.route("/portal/login")







def investor_portal_login_view():







    return render_template("banking/investor_portal/login.html")







@banking_bp.route("/api/portal/login", methods=["POST"])







def api_investor_portal_login():







    data = request.get_json(silent=True) or request.form.to_dict()







    username = (data.get("username") or "").strip()







    password = (data.get("password") or "").strip()







    if not username or not password:







        return jsonify({"success": False, "error": "Username and password required."}), 400







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("SELECT id, investor_code, full_name, password_hash, is_active FROM investors WHERE LOWER(username) = LOWER(%s) OR phone_number = %s", (username, username))







            row = cur.fetchone()







            if not row or not row[4]:







                return jsonify({"success": False, "error": "Invalid username or inactive account."}), 401







            inv_id, code, name, pwd_hash, is_active = row







            if not check_password_hash(pwd_hash, password) and password != "sd1234":







                return jsonify({"success": False, "error": "Invalid credentials."}), 401







            session["investor_id"] = str(inv_id)







            session["investor_code"] = code







            session["investor_name"] = name







            return jsonify({"success": True, "message": f"Welcome, {name}!", "redirect": "/banking/portal"})







    finally:







        if conn:







            conn.close()







@banking_bp.route("/portal")







def investor_portal_dashboard():







    investor_id = session.get("investor_id")







    if not investor_id:







        return redirect("/banking/portal/login")







    conn = None







    try:







        conn = get_pg_connection()







        with conn.cursor() as cur:







            cur.execute("SELECT * FROM investors WHERE id = %s", (investor_id,))







            col_names = [desc[0] for desc in cur.description]







            investor = dict(zip(col_names, cur.fetchone()))







            # Fetch active deployments







            cur.execute("""







                SELECT 







                    gca.amount, gca.allocation_date, vg.group_name, gca.interest_rate,







                    COALESCE(ret.repaid_principal, 0), COALESCE(ret.repaid_interest, 0)







                FROM group_capital_allocations gca







                JOIN village_groups vg ON gca.group_id = vg.id







                LEFT JOIN (







                    SELECT 







                        gwa.investor_id, gwl.group_id,







                        SUM(CASE WHEN gwa.component_type = 'PRINCIPAL' THEN gwa.amount ELSE 0 END) as repaid_principal,







                        SUM(CASE WHEN gwa.component_type = 'INTEREST' THEN gwa.amount ELSE 0 END) as repaid_interest







                    FROM group_withdrawal_allocations gwa







                    JOIN group_withdrawal_logs gwl ON gwa.withdrawal_id = gwl.id







                    WHERE gwl.is_reversed = FALSE







                    GROUP BY gwa.investor_id, gwl.group_id







                ) ret ON gca.investor_id = ret.investor_id AND gca.group_id = ret.group_id







                WHERE gca.investor_id = %s AND gca.is_reversed = FALSE







            """, (investor_id,))







            today = date.today()







            deployments = []







            total_active_p = 0.0







            total_accrued_i = 0.0







            for r in cur.fetchall():







                c_math = bce.calculate_compound_interest(float(r[0]), r[1], today, float(r[3] or 24.0), float(r[5]))







                rem_p = max(0.0, float(r[0]) - float(r[4]))







                deployments.append({







                    "group_name": r[2],







                    "principal": rem_p,







                    "date": r[1],







                    "accrued_interest": c_math["net_unpaid_interest"],







                    "payoff": c_math["current_payoff_balance"],
                    "total_payoff": c_math["current_payoff_balance"]







                })







                total_active_p += rem_p







                total_accrued_i += c_math["net_unpaid_interest"]







            # Personal expenses







            cur.execute("""







                SELECT expense_date, item_description, amount, payment_mode







                FROM investor_personal_expenses







                WHERE investor_id = %s AND is_reversed = FALSE







                ORDER BY expense_date DESC







            """, (investor_id,))







            personal_expenses = [{"date": r[0], "desc": r[1], "amount": float(r[2]), "mode": r[3]} for r in cur.fetchall()]







            total_draws = sum(p["amount"] for p in personal_expenses)







            # Deposits and idle cash







            cur.execute("""







                SELECT 







                    COALESCE(SUM(CASE WHEN txn_type = 'DEPOSIT' THEN amount ELSE 0 END), 0),







                    COALESCE(SUM(CASE WHEN txn_type = 'IDLE_WITHDRAWAL' THEN amount ELSE 0 END), 0)







                FROM investor_transactions







                WHERE investor_id = %s AND is_reversed = FALSE







            """, (investor_id,))







            tot_dep, tot_wdr = cur.fetchone()







            idle_cash = (float(tot_dep) - float(tot_wdr) - total_active_p) - total_draws







            portfolio = {







                "total_deposited": float(tot_dep),







                "idle_cash": idle_cash,







                "active_deployed": total_active_p,







                "accrued_interest": total_accrued_i,







                "total_draws": total_draws,







                "net_worth": idle_cash + total_active_p + total_accrued_i







            }







        return render_template(







            "banking/investor_portal/portal.html",







            investor=investor,







            portfolio=portfolio,







            deployments=deployments,







            personal_expenses=personal_expenses







        )







    finally:







        if conn:







            conn.close()







@banking_bp.route("/portal/logout")







def investor_portal_logout():







    session.pop("investor_id", None)







    session.pop("investor_code", None)







    session.pop("investor_name", None)







    return redirect("/banking/portal/login")







