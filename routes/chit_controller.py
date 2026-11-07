import os
import math
import json
import uuid
import logging
from collections import defaultdict
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, g, flash
from db import get_pg_connection
import services.chit_calc_engine as ce
from services.chit_calc_engine import round_curr
from services.interest_calc_engine import calculate_days_30_360, calculate_accrued_interest_30_360

logger = logging.getLogger(__name__)

chit_bp = Blueprint('chit_bp', __name__, url_prefix='/chit')

def is_chit_api_request():
    return (
        request.path.startswith("/chit/api/")
        or request.path.startswith("/api/")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.is_json
        or "application/json" in request.headers.get("Accept", "")
    )

def get_current_actor():
    return session.get('username') or 'Admin'

def get_current_actor_role():
    level = session.get('level')
    if level:
        return level.upper()
    return 'ADMIN'

@chit_bp.before_request
def require_chit_auth():
    user_id = session.get("user_id")
    if not user_id:
        session.modified = False
        if is_chit_api_request():
            return jsonify({
                "success": False,
                "error": "Session expired. Please login again.",
                "session_expired": True
            }), 401
        return redirect("/login")

    user_level = session.get("level")
    if user_level in ("j", "m", "s"):
        if is_chit_api_request():
            return jsonify({"success": False, "error": "Access denied."}), 403
        if session.get("download_authorized") is True:
            return redirect("/app/portal")
        else:
            session.clear()
            flash("Access denied.")
            return redirect("/login")

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

COMPANY_NAME = "Siva Durga Chit Fund"
CURRENCY_SYMBOL = "₹"

def format_month_year(my_str):
    if not my_str:
        return ''
    try:
        dt = datetime.strptime(my_str, "%Y-%m")
        return dt.strftime("%b %Y")
    except Exception:
        return my_str

def format_time_ago(dt):
    if not dt:
        return 'recently'
    try:
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        tz = getattr(dt, 'tzinfo', None)
        now = datetime.now(tz) if tz else datetime.now()
        diff = now - dt
        secs = int(diff.total_seconds())
        if secs < 0:
            return 'just now'
        if secs < 60:
            return f"{max(1, secs)}s ago"
        mins = secs // 60
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 30:
            return f"{days}d ago"
        months = days // 30
        return f"{months}mo ago"
    except Exception:
        return 'recently'

def ensure_chit_schema(cur):
    try:
        cur.execute("ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS customer_id VARCHAR(5);")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chit_members_customer_id_unique') THEN
                    ALTER TABLE chit_members ADD CONSTRAINT chit_members_customer_id_unique UNIQUE (customer_id);
                END IF;
            END $$;
        """)
        cur.execute("ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS account_number VARCHAR(50);")
        cur.execute("ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS installment_type VARCHAR(20) DEFAULT 'incremental';")
        cur.execute("ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS default_installment_type VARCHAR(20) DEFAULT 'incremental';")
        cur.execute("ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS govt_id_number VARCHAR(100);")
        cur.execute("ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS govt_id_type VARCHAR(50);")
        cur.execute("ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS is_defaulted BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS defaulted_manually BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS defaulted_reason TEXT;")
        cur.execute("ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS defaulted_at TIMESTAMP WITH TIME ZONE;")
        cur.execute("ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS linked_group_id UUID;")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chit_members_linked_group ON chit_members(linked_group_id);")

        cur.execute("""
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS name VARCHAR(255);
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS chit_total_value NUMERIC(14, 2);
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS duration_months INT;
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS total_members INT;
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS monthly_installment NUMERIC(14, 2);
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS commission_percent NUMERIC(5, 2) DEFAULT 5.0;
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS foreman_commission_percent NUMERIC(5, 2) DEFAULT 5.0;
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS foreman_monthly_earnings NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS start_month_year VARCHAR(7);
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(50) DEFAULT 'Standard';
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS rules_notes TEXT;
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS is_month1_company_month BOOLEAN DEFAULT TRUE;
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE chit_groups ADD COLUMN IF NOT EXISTS delete_reason TEXT;
            
            ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS govt_id_last4 VARCHAR(4);
            ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS member_portal_enabled BOOLEAN DEFAULT FALSE;
            ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS nominee_name VARCHAR(255);
            ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS nominee_phone VARCHAR(20);
            ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS nominee_relation VARCHAR(50);
            ALTER TABLE chit_members ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
            
            ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS chit_group_id UUID REFERENCES chit_groups(id) ON DELETE CASCADE;
            ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS share_units NUMERIC(5, 2) DEFAULT 1.0;
            ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS has_lifted BOOLEAN DEFAULT FALSE;
            ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS lifted_month_index INT;
            ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS start_month_index INT DEFAULT 1;
            ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS is_pool_split BOOLEAN DEFAULT FALSE;
            ALTER TABLE chit_memberships ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
            UPDATE chit_memberships SET created_at = joined_at WHERE created_at IS NULL AND joined_at IS NOT NULL;
            
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS chit_group_id UUID REFERENCES chit_groups(id) ON DELETE CASCADE;
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS chit_loss NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS amount_received NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS bonus NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS installment_kattubadi NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS is_company_month BOOLEAN DEFAULT FALSE;
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS lifted_by_membership_id UUID REFERENCES chit_memberships(id);
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS payout_date DATE;
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS payout_status VARCHAR(50);
            ALTER TABLE chit_schedules ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Open';
            
            ALTER TABLE chit_audit_logs ADD COLUMN IF NOT EXISTS actor_name VARCHAR(255);
            ALTER TABLE chit_audit_logs ADD COLUMN IF NOT EXISTS actor_role VARCHAR(100);
            ALTER TABLE chit_audit_logs ADD COLUMN IF NOT EXISTS entity_type VARCHAR(100);
            ALTER TABLE chit_audit_logs ADD COLUMN IF NOT EXISTS entity_id VARCHAR(255);
            
            ALTER TABLE chit_installments ADD COLUMN IF NOT EXISTS chit_group_id UUID REFERENCES chit_groups(id) ON DELETE CASCADE;
            ALTER TABLE chit_installments ADD COLUMN IF NOT EXISTS month_index INT;
            ALTER TABLE chit_installments ADD COLUMN IF NOT EXISTS month_year VARCHAR(7);
            ALTER TABLE chit_installments ADD COLUMN IF NOT EXISTS gross_amount NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_installments ADD COLUMN IF NOT EXISTS net_due_amount NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_installments ADD COLUMN IF NOT EXISTS pending_amount NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_installments ADD COLUMN IF NOT EXISTS kattubadi_due NUMERIC(14, 2) DEFAULT 0;
            ALTER TABLE chit_installments ADD COLUMN IF NOT EXISTS bonus_discount NUMERIC(14, 2) DEFAULT 0;
        """)

        # Gracefully drop legacy NOT NULL constraints from earlier draft replication schemas
        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chit_groups_group_code_key') THEN
                    ALTER TABLE chit_groups DROP CONSTRAINT chit_groups_group_code_key;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_groups' AND column_name = 'group_code') THEN
                    ALTER TABLE chit_groups ALTER COLUMN group_code DROP NOT NULL;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_groups' AND column_name = 'group_name') THEN
                    ALTER TABLE chit_groups ALTER COLUMN group_name DROP NOT NULL;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_groups' AND column_name = 'total_months') THEN
                    ALTER TABLE chit_groups ALTER COLUMN total_months DROP NOT NULL;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_groups' AND column_name = 'pot_amount') THEN
                    ALTER TABLE chit_groups ALTER COLUMN pot_amount DROP NOT NULL;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_groups' AND column_name = 'start_month') THEN
                    ALTER TABLE chit_groups ALTER COLUMN start_month DROP NOT NULL;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_memberships' AND column_name = 'group_id') THEN
                    ALTER TABLE chit_memberships ALTER COLUMN group_id DROP NOT NULL;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_schedules' AND column_name = 'group_id') THEN
                    ALTER TABLE chit_schedules ALTER COLUMN group_id DROP NOT NULL;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_installments' AND column_name = 'schedule_id') THEN
                    ALTER TABLE chit_installments ALTER COLUMN schedule_id DROP NOT NULL;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_installments' AND column_name = 'base_amount') THEN
                    ALTER TABLE chit_installments ALTER COLUMN base_amount DROP NOT NULL;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chit_installments' AND column_name = 'net_due') THEN
                    ALTER TABLE chit_installments ALTER COLUMN net_due DROP NOT NULL;
                END IF;
            END $$;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chit_loans (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                member_id UUID NOT NULL REFERENCES chit_members(id),
                principal_amount NUMERIC(14, 2) NOT NULL,
                annual_interest_rate NUMERIC(6, 2) NOT NULL,
                compounding_frequency VARCHAR(20) DEFAULT 'yearly',
                disbursal_date DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                total_repaid_principal NUMERIC(14, 2) DEFAULT 0,
                total_repaid_interest NUMERIC(14, 2) DEFAULT 0,
                settled_at TIMESTAMP WITH TIME ZONE,
                settlement_type VARCHAR(40),
                settled_from_schedule_id UUID REFERENCES chit_schedules(id),
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS chit_loan_repayments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                loan_id UUID NOT NULL REFERENCES chit_loans(id) ON DELETE CASCADE,
                repayment_date DATE NOT NULL,
                principal_amount NUMERIC(14, 2) DEFAULT 0,
                interest_amount NUMERIC(14, 2) DEFAULT 0,
                total_amount NUMERIC(14, 2) NOT NULL,
                payment_mode VARCHAR(40) DEFAULT 'Cash',
                receipt_no VARCHAR(50),
                source_schedule_id UUID REFERENCES chit_schedules(id),
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS chit_credit_transfers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                member_id UUID NOT NULL REFERENCES chit_members(id) ON DELETE CASCADE,
                from_group_id UUID NOT NULL REFERENCES chit_groups(id) ON DELETE CASCADE,
                from_membership_id UUID REFERENCES chit_memberships(id) ON DELETE SET NULL,
                to_group_id UUID NOT NULL REFERENCES chit_groups(id) ON DELETE CASCADE,
                to_membership_id UUID REFERENCES chit_memberships(id) ON DELETE SET NULL,
                amount NUMERIC(14, 2) NOT NULL,
                notes TEXT,
                transferred_by VARCHAR(100),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_chit_loans_member ON chit_loans(member_id);
            CREATE INDEX IF NOT EXISTS idx_chit_loans_status ON chit_loans(status);
            CREATE INDEX IF NOT EXISTS idx_chit_loan_repayments_loan ON chit_loan_repayments(loan_id);
            CREATE INDEX IF NOT EXISTS idx_chit_credit_transfers_member ON chit_credit_transfers(member_id);
            CREATE INDEX IF NOT EXISTS idx_chit_credit_transfers_from_grp ON chit_credit_transfers(from_group_id);
            CREATE INDEX IF NOT EXISTS idx_chit_credit_transfers_to_grp ON chit_credit_transfers(to_group_id);
        """)
    except Exception as e:
        print(f"[WARN] ensure_chit_schema: {e}")

# Run schema check once on import
try:
    _conn = get_pg_connection()
    _cur = _conn.cursor()
    ensure_chit_schema(_cur)
    _conn.commit()
    _cur.close()
    _conn.close()
except Exception:
    pass

# -------------------------------------------------------------
# PAGE ROUTES
# -------------------------------------------------------------

@chit_bp.route('/dashboard')
def chit_dashboard():
    return render_template('chit/dashboard.html')

@chit_bp.route('/groups')
def chit_groups_page():
    return render_template('chit/groups.html')

@chit_bp.route('/groups/new')
def chit_groups_new_page():
    return render_template('chit/groups_new.html')

@chit_bp.route('/groups/<group_id>/edit')
def chit_groups_edit_page(group_id):
    return render_template('chit/groups_edit.html', group_id=group_id)

@chit_bp.route('/schedules')
@chit_bp.route('/auctions')
@chit_bp.route('/lifts')
@chit_bp.route('/payouts')
def chit_auctions_page():
    return render_template('chit/auctions.html')

@chit_bp.route('/members')
def chit_members_page():
    return render_template('chit/members.html')

@chit_bp.route('/members/new')
def chit_member_new_page():
    return render_template('chit/member_form.html', is_edit=False, member_id=None)

@chit_bp.route('/members/<member_id>/edit')
def chit_member_edit_page(member_id):
    return render_template('chit/member_form.html', is_edit=True, member_id=member_id)

@chit_bp.route('/members/<member_id>')
def chit_member_detail_page(member_id):
    return render_template('chit/member_detail.html', member_id=member_id)

@chit_bp.route('/loans')
def chit_loans_page():
    return render_template('chit/loans.html')

@chit_bp.route('/accounting')
def chit_accounting_page():
    return render_template('chit/accounting.html')

@chit_bp.route('/reports')
def chit_reports_page():
    return render_template('chit/reports.html')

@chit_bp.route('/settings')
def chit_settings_page():
    return redirect('/chit/accounting')

@chit_bp.route('/activity')
def chit_activity_page():
    return render_template('chit/activity.html')

# -------------------------------------------------------------
# GLOBAL SEARCH API
# -------------------------------------------------------------

@chit_bp.route('/api/search', methods=['GET'])
def chit_global_search():
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify({'members': [], 'groups': []})

    pattern = f'%{q}%'
    conn = get_pg_connection()
    cur = conn.cursor()
    results = {'members': [], 'groups': []}

    try:
        # Search members
        cur.execute("""
            SELECT id, full_name, phone, customer_id
            FROM chit_members
            WHERE full_name ILIKE %s OR phone ILIKE %s OR
                  customer_id ILIKE %s OR govt_id_number ILIKE %s
            ORDER BY full_name
            LIMIT 10;
        """, (pattern, pattern, pattern, pattern))
        for row in cur.fetchall():
            results['members'].append({
                'id': str(row[0]),
                'name': row[1] or '',
                'phone': row[2] or '',
                'customer_id': row[3] or '',
            })

        # Search groups
        cur.execute("""
            SELECT id, name, chit_total_value, status, total_members
            FROM chit_groups
            WHERE deleted_at IS NULL AND (
                name ILIKE %s OR CAST(chit_total_value AS TEXT) ILIKE %s
            )
            ORDER BY name
            LIMIT 10;
        """, (pattern, pattern))
        for row in cur.fetchall():
            results['groups'].append({
                'id': str(row[0]),
                'name': row[1] or '',
                'chit_value': float(row[2]) if row[2] else 0,
                'status': row[3] or '',
            })
    except Exception as e:
        print(f"[WARN] chit_global_search: {e}")
    finally:
        cur.close()
        conn.close()

    return jsonify(results)

# -------------------------------------------------------------
# MEMBER LOANS & ANNUAL COMPOUND INTEREST ENGINE
# -------------------------------------------------------------

def calculate_loan_compound_interest(principal, annual_rate, disbursal_date, as_of_date=None, repaid_principal=0.0, repaid_interest=0.0):
    """Calculates member loan interest and payoff using the unified 30/360 interest engine."""
    if as_of_date is None:
        as_of_date = date.today()
    p_orig = float(principal or 0)
    p_rep = float(repaid_principal or 0)
    i_rep = float(repaid_interest or 0)
    p_rem = max(0.0, p_orig - p_rep)
    rate = float(annual_rate or 0)

    res = calculate_accrued_interest_30_360(
        principal=p_rem,
        annual_rate=rate,
        start_date=disbursal_date,
        as_of_date=as_of_date,
        repaid_interest=i_rep,
    )

    days_elapsed = res["days_elapsed"]
    t_years = round(days_elapsed / 360.0, 3)

    return {
        'days_elapsed': days_elapsed,
        'years_elapsed': t_years,
        'original_principal': round_curr(p_orig),
        'repaid_principal': round_curr(p_rep),
        'remaining_principal': round_curr(p_rem),
        'repaid_interest': round_curr(i_rep),
        'accrued_interest': round_curr(res["net_unpaid_interest"]),
        'total_payoff': round_curr(res["current_payoff_balance"])
    }

@chit_bp.route('/api/loans/eligible-members', methods=['GET'])
def get_loan_eligible_members():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT m.id::text, m.full_name, m.phone, m.customer_id
            FROM chit_members m
            JOIN chit_memberships ms ON m.id = ms.member_id
            JOIN chit_groups g ON ms.chit_group_id = g.id
            WHERE g.deleted_at IS NULL AND g.status = 'Active'
            ORDER BY m.full_name;
        """)
        rows = cur.fetchall()
        members = [{'id': r[0], 'name': r[1], 'phone': r[2] or '', 'customer_id': r[3] or ''} for r in rows]
        return jsonify({'success': True, 'members': members})
    except Exception as e:
        print(f"[WARN] get_loan_eligible_members: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/loans/member-commitments/<member_id>', methods=['GET'])
def get_member_commitments(member_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # 1. Member Basic Details
        cur.execute("SELECT id::text, full_name, phone, customer_id FROM chit_members WHERE id::text = %s;", (member_id,))
        m_row = cur.fetchone()
        if not m_row:
            return jsonify({'success': False, 'error': 'Member not found'}), 404

        # 2. Enrolled Chit Groups & Monthly Commitments
        cur.execute("""
            SELECT 
                g.id::text,
                g.name,
                g.chit_total_value,
                g.monthly_installment,
                g.duration_months,
                g.current_month_index,
                ms.ticket_number,
                COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                ms.has_lifted,
                COALESCE(SUM(i.pending_amount), 0) as total_pending
            FROM chit_memberships ms
            JOIN chit_groups g ON ms.chit_group_id = g.id
            LEFT JOIN chit_installments i ON ms.id = i.membership_id AND i.pending_amount > 0
            WHERE ms.member_id::text = %s AND g.deleted_at IS NULL AND g.status = 'Active'
            GROUP BY g.id, g.name, g.chit_total_value, g.monthly_installment, g.duration_months, g.current_month_index, ms.ticket_number, ms.account_number, ms.has_lifted
            ORDER BY g.name;
        """, (member_id,))
        chits_rows = cur.fetchall()

        active_chits = []
        total_monthly_commitment = 0.0
        total_overdue = 0.0

        for cr in chits_rows:
            inst_val = float(cr[3] or 0)
            pend_val = float(cr[9] or 0)
            total_monthly_commitment += inst_val
            total_overdue += pend_val

            active_chits.append({
                'group_id': cr[0],
                'group_name': cr[1],
                'chit_value': float(cr[2] or 0),
                'monthly_installment': inst_val,
                'duration_months': cr[4],
                'current_month': cr[5],
                'ticket_number': cr[6],
                'account_number': cr[7],
                'has_lifted': bool(cr[8]),
                'pending_amount': pend_val
            })

        # 3. Existing Active Loans for this Member
        cur.execute("""
            SELECT id::text, principal_amount, annual_interest_rate, disbursal_date::text, status,
                   total_repaid_principal, total_repaid_interest, notes
            FROM chit_loans
            WHERE member_id::text = %s AND status = 'active'
            ORDER BY disbursal_date DESC;
        """, (member_id,))
        loan_rows = cur.fetchall()
        existing_loans = []
        for lr in loan_rows:
            calc = calculate_loan_compound_interest(
                principal=lr[1],
                annual_rate=lr[2],
                disbursal_date=lr[3],
                repaid_principal=lr[5],
                repaid_interest=lr[6]
            )
            existing_loans.append({
                'id': lr[0],
                'principal': float(lr[1] or 0),
                'rate': float(lr[2] or 0),
                'disbursal_date': lr[3],
                'accrued_interest': calc['accrued_interest'],
                'total_payoff': calc['total_payoff'],
                'notes': lr[7] or ''
            })

        return jsonify({
            'success': True,
            'member': {
                'id': m_row[0],
                'name': m_row[1],
                'phone': m_row[2] or '',
                'customer_id': m_row[3] or ''
            },
            'active_chits': active_chits,
            'total_monthly_commitment': total_monthly_commitment,
            'total_overdue': total_overdue,
            'existing_loans': existing_loans
        })
    except Exception as e:
        print(f"[WARN] get_member_commitments: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/loans', methods=['GET', 'POST'])
def handle_loans_collection():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        if request.method == 'GET':
            status_filter = request.args.get('status', 'all').lower()
            member_id_filter = request.args.get('member_id')

            where_clauses = ["1=1"]
            params = []

            if status_filter in ('active', 'settled', 'defaulted'):
                where_clauses.append("l.status = %s")
                params.append(status_filter)

            if member_id_filter:
                where_clauses.append("l.member_id::text = %s")
                params.append(member_id_filter)

            where_sql = " AND ".join(where_clauses)
            cur.execute(f"""
                SELECT 
                    l.id::text,
                    l.member_id::text,
                    m.full_name,
                    m.phone,
                    m.customer_id,
                    l.principal_amount,
                    l.annual_interest_rate,
                    l.compounding_frequency,
                    l.disbursal_date::text,
                    l.status,
                    l.total_repaid_principal,
                    l.total_repaid_interest,
                    l.settled_at::text,
                    l.settlement_type,
                    l.notes,
                    l.created_at::text,
                    (
                        SELECT COUNT(DISTINCT ms.chit_group_id) 
                        FROM chit_memberships ms 
                        JOIN chit_groups g ON ms.chit_group_id = g.id 
                        WHERE ms.member_id = l.member_id AND g.deleted_at IS NULL AND g.status = 'Active'
                    ) as active_chits_count
                FROM chit_loans l
                JOIN chit_members m ON l.member_id = m.id
                WHERE {where_sql}
                ORDER BY l.disbursal_date DESC, l.created_at DESC;
            """, tuple(params))
            rows = cur.fetchall()

            loans = []
            tot_active_principal = 0.0
            tot_accrued_interest = 0.0
            tot_recovered_principal = 0.0
            tot_recovered_interest = 0.0
            unique_borrowers = set()

            for r in rows:
                p_orig = float(r[5] or 0)
                r_rate = float(r[6] or 0)
                d_date = r[8]
                r_prep = float(r[10] or 0)
                r_irep = float(r[11] or 0)
                l_status = r[9]

                tot_recovered_principal += r_prep
                tot_recovered_interest += r_irep

                calc = calculate_loan_compound_interest(
                    principal=p_orig,
                    annual_rate=r_rate,
                    disbursal_date=d_date,
                    repaid_principal=r_prep,
                    repaid_interest=r_irep
                )

                if l_status == 'active':
                    tot_active_principal += calc['remaining_principal']
                    tot_accrued_interest += calc['accrued_interest']
                    unique_borrowers.add(r[1])

                loans.append({
                    'id': r[0],
                    'member_id': r[1],
                    'member_name': r[2],
                    'phone': r[3] or '',
                    'customer_id': r[4] or '',
                    'principal_amount': p_orig,
                    'annual_interest_rate': r_rate,
                    'compounding_frequency': r[7] or 'yearly',
                    'disbursal_date': d_date,
                    'status': l_status,
                    'repaid_principal': r_prep,
                    'repaid_interest': r_irep,
                    'settled_at': r[12],
                    'settlement_type': r[13],
                    'notes': r[14] or '',
                    'active_chits_count': r[16] or 0,
                    'days_elapsed': calc['days_elapsed'],
                    'remaining_principal': calc['remaining_principal'],
                    'accrued_interest': calc['accrued_interest'],
                    'total_payoff': calc['total_payoff']
                })

            summary = {
                'total_active_principal': round_curr(tot_active_principal),
                'total_accrued_interest': round_curr(tot_accrued_interest),
                'total_recovered_principal': round_curr(tot_recovered_principal),
                'total_recovered_interest': round_curr(tot_recovered_interest),
                'total_active_borrowers': len(unique_borrowers),
                'total_loans_count': len(loans)
            }

            return jsonify({'success': True, 'loans': loans, 'summary': summary})

        elif request.method == 'POST':
            # Disburse new loan
            data = request.get_json() or {}
            member_id = data.get('member_id')
            principal = float(data.get('principal_amount') or 0)
            rate = float(data.get('annual_interest_rate') or 18.0)
            disbursal_date = data.get('disbursal_date') or str(date.today())
            notes = (data.get('notes') or '').strip()

            if not member_id:
                return jsonify({'success': False, 'error': 'Member is required'}), 400
            if principal <= 0:
                return jsonify({'success': False, 'error': 'Principal amount must be greater than 0'}), 400
            if rate < 0:
                return jsonify({'success': False, 'error': 'Interest rate cannot be negative'}), 400

            # Eligibility Check: Must be in at least 1 active chit group
            cur.execute("""
                SELECT COUNT(*) 
                FROM chit_memberships ms
                JOIN chit_groups g ON ms.chit_group_id = g.id
                WHERE ms.member_id::text = %s AND g.deleted_at IS NULL AND g.status = 'Active';
            """, (member_id,))
            enrolled_count = int(cur.fetchone()[0] or 0)
            if enrolled_count == 0:
                return jsonify({'success': False, 'error': 'Loan eligibility failed: Customer must be enrolled in at least one active chit group.'}), 400

            loan_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO chit_loans (
                    id, member_id, principal_amount, annual_interest_rate,
                    compounding_frequency, disbursal_date, status, notes
                ) VALUES (%s, %s, %s, %s, 'yearly', %s, 'active', %s);
            """, (loan_id, member_id, principal, rate, disbursal_date, notes))

            # Audit log
            cur.execute("""
                INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
                VALUES (%s, %s, 'LOAN_DISBURSED', 'CHIT_LOAN', %s, %s);
            """, (
                get_current_actor(),
                get_current_actor_role(),
                loan_id,
                json.dumps({'principal': principal, 'rate': rate, 'disbursal_date': disbursal_date, 'member_id': member_id})
            ))

            conn.commit()
            return jsonify({'success': True, 'loan_id': loan_id, 'message': 'Loan disbursed successfully'})
        return jsonify({'error': 'Method not allowed'}), 405
    except Exception as e:
        conn.rollback()
        print(f"[WARN] handle_loans_collection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/loans/<loan_id>/repay', methods=['POST'])
def repay_loan(loan_id):
    data = request.get_json() or {}
    p_amt = float(data.get('principal_amount') or 0)
    i_amt = float(data.get('interest_amount') or 0)
    tot_amt = p_amt + i_amt
    pay_mode = data.get('payment_mode') or 'Cash'
    receipt_no = data.get('receipt_no') or f"LRCP-{str(uuid.uuid4())[:6].upper()}"
    notes = (data.get('notes') or '').strip()
    repay_date = data.get('repayment_date') or str(date.today())

    if tot_amt <= 0:
        return jsonify({'success': False, 'error': 'Repayment amount must be greater than zero'}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT principal_amount, annual_interest_rate, disbursal_date, total_repaid_principal, total_repaid_interest, status
            FROM chit_loans WHERE id::text = %s;
        """, (loan_id,))
        l_row = cur.fetchone()
        if not l_row:
            return jsonify({'success': False, 'error': 'Loan not found'}), 404

        p_orig, r_rate, d_date, r_prep, r_irep, l_status = l_row
        new_prep = float(r_prep or 0) + p_amt
        new_irep = float(r_irep or 0) + i_amt

        calc = calculate_loan_compound_interest(
            principal=p_orig,
            annual_rate=r_rate,
            disbursal_date=d_date,
            as_of_date=repay_date,
            repaid_principal=new_prep,
            repaid_interest=new_irep
        )

        is_settled = (calc['total_payoff'] <= 0.01)
        new_status = 'settled' if is_settled else 'active'
        settled_at = repay_date if is_settled else None
        settle_type = 'manual' if is_settled else None

        cur.execute("""
            UPDATE chit_loans 
            SET total_repaid_principal = %s,
                total_repaid_interest = %s,
                status = %s,
                settled_at = %s,
                settlement_type = %s,
                updated_at = NOW()
            WHERE id::text = %s;
        """, (new_prep, new_irep, new_status, settled_at, settle_type, loan_id))

        repay_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO chit_loan_repayments (
                id, loan_id, repayment_date, principal_amount, interest_amount,
                total_amount, payment_mode, receipt_no, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (repay_id, loan_id, repay_date, p_amt, i_amt, tot_amt, pay_mode, receipt_no, notes))

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'LOAN_REPAYMENT', 'CHIT_LOAN', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            loan_id,
            json.dumps({'total_repaid': tot_amt, 'principal': p_amt, 'interest': i_amt, 'is_settled': is_settled})
        ))

        conn.commit()
        return jsonify({
            'success': True,
            'is_settled': is_settled,
            'remaining_payoff': calc['total_payoff'],
            'message': 'Loan settled in full!' if is_settled else 'Repayment recorded successfully'
        })
    except Exception as e:
        conn.rollback()
        print(f"[WARN] repay_loan: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/loans/<loan_id>/details', methods=['GET'])
def get_loan_details(loan_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                l.id::text, l.member_id::text, m.full_name, m.phone, m.customer_id,
                l.principal_amount, l.annual_interest_rate, l.compounding_frequency,
                l.disbursal_date::text, l.status, l.total_repaid_principal, l.total_repaid_interest,
                l.settled_at::text, l.settlement_type, l.notes, l.created_at::text
            FROM chit_loans l
            JOIN chit_members m ON l.member_id = m.id
            WHERE l.id::text = %s;
        """, (loan_id,))
        lr = cur.fetchone()
        if not lr:
            return jsonify({'success': False, 'error': 'Loan not found'}), 404

        calc = calculate_loan_compound_interest(
            principal=lr[5],
            annual_rate=lr[6],
            disbursal_date=lr[8],
            repaid_principal=lr[10],
            repaid_interest=lr[11]
        )

        cur.execute("""
            SELECT id::text, repayment_date::text, principal_amount, interest_amount, total_amount, payment_mode, receipt_no, notes
            FROM chit_loan_repayments
            WHERE loan_id::text = %s
            ORDER BY repayment_date DESC, created_at DESC;
        """, (loan_id,))
        reps = cur.fetchall()
        repayments = []
        for rp in reps:
            repayments.append({
                'id': rp[0],
                'date': rp[1],
                'principal': float(rp[2] or 0),
                'interest': float(rp[3] or 0),
                'total': float(rp[4] or 0),
                'mode': rp[5],
                'receipt_no': rp[6] or '',
                'notes': rp[7] or ''
            })

        return jsonify({
            'success': True,
            'loan': {
                'id': lr[0],
                'member_id': lr[1],
                'member_name': lr[2],
                'phone': lr[3] or '',
                'customer_id': lr[4] or '',
                'principal_amount': float(lr[5] or 0),
                'annual_interest_rate': float(lr[6] or 0),
                'compounding_frequency': lr[7],
                'disbursal_date': lr[8],
                'status': lr[9],
                'repaid_principal': float(lr[10] or 0),
                'repaid_interest': float(lr[11] or 0),
                'settled_at': lr[12],
                'settlement_type': lr[13],
                'notes': lr[14] or '',
                'calculation': calc,
                'repayments': repayments
            }
        })
    except Exception as e:
        print(f"[WARN] get_loan_details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# -------------------------------------------------------------
def get_member_active_loan_payoff(cur, member_id, as_of_date=None):
    if not member_id:
        return 0.0
    cur.execute("""
        SELECT principal_amount, annual_interest_rate, disbursal_date,
               total_repaid_principal, total_repaid_interest
        FROM chit_loans
        WHERE member_id::text = %s AND status = 'active';
    """, (str(member_id),))
    loans = cur.fetchall()
    total_payoff = 0.0
    for lr in loans:
        calc = calculate_loan_compound_interest(
            principal=lr[0], annual_rate=lr[1], disbursal_date=lr[2],
            as_of_date=as_of_date, repaid_principal=lr[3], repaid_interest=lr[4]
        )
        total_payoff += calc['total_payoff']
    return total_payoff
# ACCOUNTING & FORECASTING API
# -------------------------------------------------------------

@chit_bp.route('/api/accounting/overview', methods=['GET'])
def get_accounting_overview():
    period = request.args.get('period', 'today').lower()
    pay_mode = request.args.get('mode', 'all').lower()
    
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # 1. Total Inflows (Chit Collections + Loan Repayments) - Exclude non-cash advance credit settlements
        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment') THEN amount ELSE 0 END), 0) as total_inflow,
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(payment_mode, 'cash')) = 'cash' THEN amount ELSE 0 END), 0) as cash_inflow,
                COALESCE(SUM(CASE WHEN LOWER(payment_mode) = 'upi' THEN amount ELSE 0 END), 0) as upi_inflow,
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(payment_mode, 'cash')) NOT IN ('cash', 'upi', 'advance credit', 'credit settlement', 'credit adjustment') THEN amount ELSE 0 END), 0) as bank_inflow,
                COALESCE(SUM(CASE WHEN LOWER(payment_mode) IN ('advance credit', 'credit settlement', 'credit adjustment') THEN amount ELSE 0 END), 0) as credit_settled
            FROM chit_payments;
        """)
        inf_row = cur.fetchone()
        chit_inflow = float(inf_row[0] or 0)
        chit_cash_inflow = float(inf_row[1] or 0)
        chit_upi_inflow = float(inf_row[2] or 0)
        chit_bank_inflow = float(inf_row[3] or 0)
        chit_credit_settled = float(inf_row[4] or 0)

        # Loan Inflows (Principal repaid + Interest earned)
        cur.execute("""
            SELECT 
                COALESCE(SUM(total_amount), 0) as loan_inflow,
                COALESCE(SUM(principal_amount), 0) as loan_principal_repaid,
                COALESCE(SUM(interest_amount), 0) as loan_interest_earned,
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(payment_mode, 'cash')) = 'cash' THEN total_amount ELSE 0 END), 0) as loan_cash_inflow,
                COALESCE(SUM(CASE WHEN LOWER(payment_mode) = 'upi' THEN total_amount ELSE 0 END), 0) as loan_upi_inflow,
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(payment_mode, 'cash')) NOT IN ('cash', 'upi') THEN total_amount ELSE 0 END), 0) as loan_bank_inflow
            FROM chit_loan_repayments;
        """)
        lr_row = cur.fetchone()
        loan_inflow = float(lr_row[0] or 0)
        loan_interest_earned = float(lr_row[2] or 0)
        loan_cash_inflow = float(lr_row[3] or 0)
        loan_upi_inflow = float(lr_row[4] or 0)
        loan_bank_inflow = float(lr_row[5] or 0)

        total_inflow = chit_inflow + loan_inflow
        cash_inflow = chit_cash_inflow + loan_cash_inflow
        bank_inflow = chit_bank_inflow + loan_bank_inflow
        upi_inflow = chit_upi_inflow + loan_upi_inflow

        # 2. Total Outflows (Disbursed Prize Money + Disbursed Loans)
        cur.execute("""
            SELECT COALESCE(SUM(s.amount_received * ms.share_units), 0) as total_outflow
            FROM chit_memberships ms
            JOIN chit_groups g ON ms.chit_group_id = g.id
            LEFT JOIN chit_schedules s ON g.id = s.chit_group_id AND ms.lifted_month_index = s.month_index
            WHERE ms.has_lifted = TRUE AND ms.lifted_month_index IS NOT NULL AND g.deleted_at IS NULL;
        """)
        prize_outflow = float(cur.fetchone()[0] or 0)

        cur.execute("""
            SELECT COALESCE(SUM(principal_amount), 0) as total_loan_disbursed
            FROM chit_loans;
        """)
        loan_outflow = float(cur.fetchone()[0] or 0)

        total_outflow = prize_outflow + loan_outflow
        net_balance = total_inflow - total_outflow

        # 3. Foreman & Loan Earnings / Commission
        cur.execute("""
            SELECT COALESCE(SUM(foreman_monthly_earnings * current_month_index), 0)
            FROM chit_groups
            WHERE deleted_at IS NULL AND status = 'Active';
        """)
        chit_foreman_earnings = float(cur.fetchone()[0] or 0)
        foreman_earnings = chit_foreman_earnings + loan_interest_earned

        # 4. Total Outstanding Subscriber Dues
        cur.execute("""
            SELECT COALESCE(SUM(i.pending_amount), 0)
            FROM chit_installments i
            JOIN chit_groups g ON i.chit_group_id = g.id
            WHERE g.deleted_at IS NULL AND g.status = 'Active' AND i.pending_amount > 0 AND i.month_index <= g.current_month_index;
        """)
        total_pending_dues = float(cur.fetchone()[0] or 0)

        # 5. Counts
        cur.execute("SELECT COUNT(*) FROM chit_groups WHERE deleted_at IS NULL AND status = 'Active';")
        active_groups_count = int(cur.fetchone()[0] or 0)

        cur.execute("""
            SELECT COUNT(DISTINCT ms.member_id) 
            FROM chit_memberships ms
            JOIN chit_groups g ON ms.chit_group_id = g.id
            WHERE g.deleted_at IS NULL AND g.status = 'Active';
        """)
        active_members_count = int(cur.fetchone()[0] or 0)

        # 6. Forward Forecasting (M0, M+1, M+2, M+3, M+4)
        cur.execute("""
            SELECT id, name, chit_total_value, duration_months, current_month_index, monthly_installment, total_members, foreman_monthly_earnings, start_month_year
            FROM chit_groups
            WHERE deleted_at IS NULL AND status = 'Active'
            ORDER BY name ASC;
        """)
        active_groups = cur.fetchall()

        # Determine base current date from current month
        base_dt = date.today().replace(day=1)

        forecast = []
        for offset in range(5):
            target_dt = base_dt + relativedelta(months=offset)
            m_label = target_dt.strftime('%b %Y')
            
            planned_outflow = 0.0
            expected_inflow = 0.0
            closing_chits = []
            payout_details = []

            for g in active_groups:
                g_id, g_name, g_val, g_dur, g_curr_m, g_inst, g_members, g_earn = g[0], g[1], g[2], g[3], g[4], g[5], g[6], g[7]
                g_val = float(g_val or 0)
                g_dur = int(g_dur or 20)
                g_curr_m = int(g_curr_m or 1)
                g_inst = float(g_inst or 0)
                g_members = int(g_members or 20)
                
                target_m_idx = g_curr_m + offset

                if target_m_idx <= g_dur:
                    # Check schedule for this target_m_idx
                    cur.execute("""
                        SELECT s.installment_kattubadi, s.amount_received, s.payout_status, s.payout_date,
                               m.full_name, s.chit_loss, ms.member_id
                        FROM chit_schedules s
                        LEFT JOIN chit_memberships ms ON s.lifted_by_membership_id = ms.id
                        LEFT JOIN chit_members m ON ms.member_id = m.id
                        WHERE s.chit_group_id = %s AND s.month_index = %s;
                    """, (str(g_id), target_m_idx))
                    sched = cur.fetchone()

                    month_katt = float(sched[0]) if (sched and sched[0] is not None) else float(g_inst or 0)

                    # Query net due from installments if already generated, otherwise calculate from total assigned shares
                    cur.execute("""
                        SELECT COALESCE(SUM(net_due_amount), 0)
                        FROM chit_installments
                        WHERE chit_group_id = %s AND month_index = %s;
                    """, (str(g_id), target_m_idx))
                    inst_due_row = cur.fetchone()
                    inst_due = float(inst_due_row[0] or 0.0) if inst_due_row else 0.0

                    if inst_due > 0:
                        expected_inflow += inst_due
                    else:
                        cur.execute("SELECT COALESCE(SUM(share_units), 0) FROM chit_memberships WHERE chit_group_id = %s;", (str(g_id),))
                        tot_shares = float(cur.fetchone()[0] or 0.0)
                        expected_inflow += (tot_shares * month_katt)

                    # CASE 1: Chit Group is ENDING this month (target_m_idx == g_dur)
                    if target_m_idx == g_dur:
                        # In the final month, members who took payouts in prior months get 0!
                        # Only members with 0 payouts (unlifted chits) get the final payout.
                        cur.execute("""
                            SELECT ms.id, ms.member_id, m.full_name, ms.ticket_number, ms.share_units
                            FROM chit_memberships ms
                            JOIN chit_members m ON ms.member_id = m.id
                            WHERE ms.chit_group_id = %s AND (ms.has_lifted = FALSE OR ms.has_lifted IS NULL)
                            ORDER BY ms.ticket_number ASC;
                        """, (str(g_id),))
                        unlifted_members = cur.fetchall()

                        final_payout_per_share = float(sched[1]) if (sched and sched[1] is not None) else g_val
                        group_final_outflow = 0.0
                        unlifted_breakdown = []

                        for um in unlifted_members:
                            um_id, um_mid, um_name, um_ticket, um_shares = um
                            um_shares = float(um_shares or 1.0)
                            gross_p = final_payout_per_share * um_shares
                            # Deduct respective loan amounts and interest if borrowed
                            loan_due = get_member_active_loan_payoff(cur, um_mid, as_of_date=target_dt)
                            net_p = max(0.0, gross_p - loan_due)
                            group_final_outflow += net_p
                            unlifted_breakdown.append({
                                'member_name': um_name,
                                'ticket_number': um_ticket,
                                'share_units': um_shares,
                                'gross_payout': gross_p,
                                'loan_deduction': loan_due,
                                'net_payout': net_p
                            })

                        planned_outflow += group_final_outflow
                        closing_chits.append({
                            'id': str(g_id),
                            'name': g_name,
                            'chit_value': g_val,
                            'duration_months': g_dur,
                            'month_index': target_m_idx,
                            'final_payout': group_final_outflow,
                            'unlifted_count': len(unlifted_members),
                            'unlifted_breakdown': unlifted_breakdown
                        })

                        if group_final_outflow > 0:
                            payout_details.append({
                                'chit_id': str(g_id),
                                'chit_name': g_name,
                                'amount': group_final_outflow,
                                'winner': f"Final Payout ({len(unlifted_members)} unlifted)",
                                'status': 'closing_settlement',
                                'is_recorded': True
                            })

                    # CASE 2: Interim month (target_m_idx < g_dur)
                    else:
                        cur.execute("""
                            SELECT ms.id, ms.member_id, m.full_name, ms.ticket_number, ms.share_units
                            FROM chit_memberships ms
                            JOIN chit_members m ON ms.member_id = m.id
                            WHERE ms.chit_group_id = %s 
                              AND ((ms.has_lifted = TRUE AND ms.lifted_month_index = %s)
                                   OR ms.id IN (SELECT lifted_by_membership_id FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s AND lifted_by_membership_id IS NOT NULL));
                        """, (str(g_id), target_m_idx, str(g_id), target_m_idx))
                        target_lifted = cur.fetchall()

                        if target_lifted:
                            for t_m in target_lifted:
                                t_ms_id, t_mid, t_name, t_ticket, t_shares = t_m
                                t_shares = float(t_shares or 1.0)
                                sched_amt = float(sched[1]) if (sched and sched[1] is not None) else float(g_inst or 0)
                                gross_p = sched_amt * t_shares
                                loan_due = get_member_active_loan_payoff(cur, t_mid, as_of_date=target_dt) if t_mid else 0.0
                                net_p = max(0.0, gross_p - loan_due)
                                planned_outflow += net_p
                                payout_details.append({
                                    'chit_id': str(g_id),
                                    'chit_name': g_name,
                                    'amount': net_p,
                                    'gross_amount': gross_p,
                                    'loan_deduction': loan_due,
                                    'winner': t_name,
                                    'status': sched[2] if sched else 'paid',
                                    'is_recorded': True
                                })
                        # If no payout recorded/assigned for that month, planned_outflow remains 0!

            forecast.append({
                'offset': offset,
                'month_label': m_label,
                'is_current': offset == 0,
                'planned_outflow': planned_outflow,
                'expected_inflow': expected_inflow,
                'net_cushion': expected_inflow - planned_outflow,
                'closing_chits': closing_chits,
                'payout_details': payout_details
            })

        # 7. Master Ledger with timeframe filter
        date_cond_pay = ""
        date_cond_sched = ""
        date_cond_loan = ""
        date_cond_repay = ""
        if period == 'today':
            date_cond_pay = "AND p.payment_date = CURRENT_DATE"
            date_cond_sched = "AND COALESCE(ms.payout_date, s.payout_date) = CURRENT_DATE"
            date_cond_loan = "AND l.disbursal_date = CURRENT_DATE"
            date_cond_repay = "AND r.repayment_date = CURRENT_DATE"
        elif period == 'yesterday':
            date_cond_pay = "AND p.payment_date = CURRENT_DATE - 1"
            date_cond_sched = "AND COALESCE(ms.payout_date, s.payout_date) = CURRENT_DATE - 1"
            date_cond_loan = "AND l.disbursal_date = CURRENT_DATE - 1"
            date_cond_repay = "AND r.repayment_date = CURRENT_DATE - 1"
        elif period == '7days':
            date_cond_pay = "AND p.payment_date >= CURRENT_DATE - 7"
            date_cond_sched = "AND COALESCE(ms.payout_date, s.payout_date) >= CURRENT_DATE - 7"
            date_cond_loan = "AND l.disbursal_date >= CURRENT_DATE - 7"
            date_cond_repay = "AND r.repayment_date >= CURRENT_DATE - 7"
        elif period == '15days':
            date_cond_pay = "AND p.payment_date >= CURRENT_DATE - 15"
            date_cond_sched = "AND COALESCE(ms.payout_date, s.payout_date) >= CURRENT_DATE - 15"
            date_cond_loan = "AND l.disbursal_date >= CURRENT_DATE - 15"
            date_cond_repay = "AND r.repayment_date >= CURRENT_DATE - 15"
        elif period == 'month':
            date_cond_pay = "AND date_trunc('month', p.payment_date) = date_trunc('month', CURRENT_DATE)"
            date_cond_sched = "AND date_trunc('month', COALESCE(ms.payout_date, s.payout_date)) = date_trunc('month', CURRENT_DATE)"
            date_cond_loan = "AND date_trunc('month', l.disbursal_date) = date_trunc('month', CURRENT_DATE)"
            date_cond_repay = "AND date_trunc('month', r.repayment_date) = date_trunc('month', CURRENT_DATE)"

        mode_cond = ""
        mode_cond_repay = ""
        if pay_mode != 'all':
            mode_cond = f"AND LOWER(p.payment_mode) = '{pay_mode}'"
            mode_cond_repay = f"AND LOWER(r.payment_mode) = '{pay_mode}'"

        # Active Loan Book stats
        cur.execute("""
            SELECT 
                COUNT(*) as active_loans_count,
                COALESCE(SUM(principal_amount - total_repaid_principal), 0) as active_principal_book,
                COALESCE(SUM(total_repaid_principal), 0) as total_principal_recovered,
                COALESCE(SUM(total_repaid_interest), 0) as total_interest_recovered
            FROM chit_loans
            WHERE status = 'active';
        """)
        l_stat = cur.fetchone()
        active_loans_count = int(l_stat[0] or 0)
        active_loans_principal = float(l_stat[1] or 0)
        total_loan_recovered = float(l_stat[2] or 0) + float(l_stat[3] or 0)

        ledger_sql = f"""
            SELECT 
                p.id::text,
                p.payment_date::text as tx_date,
                'inflow' as tx_type,
                COALESCE(m.full_name, 'Subscriber') as party_name,
                COALESCE(g.name, 'Chit') as chit_name,
                COALESCE(p.receipt_no, p.reference_no, 'RCP-' || SUBSTRING(p.id::text, 1, 6)) as ref_no,
                COALESCE(p.payment_mode, 'Cash') as payment_mode,
                p.amount as amount,
                COALESCE(p.notes, 'Collection payment') as notes,
                p.created_at
            FROM chit_payments p
            LEFT JOIN chit_memberships ms ON p.membership_id = ms.id
            LEFT JOIN chit_members m ON ms.member_id = m.id
            LEFT JOIN chit_installments i ON p.installment_id = i.id
            LEFT JOIN chit_groups g ON i.chit_group_id = g.id
            WHERE 1=1 {date_cond_pay} {mode_cond}
              AND LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment')

            UNION ALL

            SELECT 
                r.id::text,
                r.repayment_date::text as tx_date,
                'inflow' as tx_type,
                COALESCE(m.full_name, 'Borrower') as party_name,
                'Loan Recovery' as chit_name,
                COALESCE(r.receipt_no, 'LRCP-' || SUBSTRING(r.id::text, 1, 6)) as ref_no,
                COALESCE(r.payment_mode, 'Cash') as payment_mode,
                r.total_amount as amount,
                'Loan Repayment (P: ₹' || ROUND(r.principal_amount, 0) || ', I: ₹' || ROUND(r.interest_amount, 0) || ') - ' || COALESCE(r.notes, '') as notes,
                r.created_at
            FROM chit_loan_repayments r
            JOIN chit_loans l ON r.loan_id = l.id
            JOIN chit_members m ON l.member_id = m.id
            WHERE 1=1 {date_cond_repay} {mode_cond_repay}

            UNION ALL

            SELECT 
                ms.id::text,
                COALESCE(ms.payout_date::text, s.payout_date::text, CURRENT_DATE::text) as tx_date,
                'outflow' as tx_type,
                COALESCE(m.full_name, 'Prize Winner') as party_name,
                g.name as chit_name,
                'PAY-' || ms.lifted_month_index || '-' || SUBSTRING(ms.id::text, 1, 6) as ref_no,
                COALESCE(SPLIT_PART(ms.payout_notes, ' · ', 1), 'Bank') as payment_mode,
                COALESCE(ms.payout_amount, (s.amount_received * COALESCE(ms.share_units, 1.0))) as amount,
                COALESCE(ms.payout_notes, s.notes, 'Prize Money Payout') as notes,
                COALESCE(ms.created_at, s.created_at, NOW()) as created_at
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            JOIN chit_groups g ON ms.chit_group_id = g.id
            LEFT JOIN chit_schedules s ON g.id = s.chit_group_id AND ms.lifted_month_index = s.month_index
            WHERE ms.has_lifted = TRUE AND ms.lifted_month_index IS NOT NULL {date_cond_sched}

            UNION ALL

            SELECT 
                l.id::text,
                l.disbursal_date::text as tx_date,
                'outflow' as tx_type,
                COALESCE(m.full_name, 'Borrower') as party_name,
                'Member Loan' as chit_name,
                'LOAN-' || SUBSTRING(l.id::text, 1, 6) as ref_no,
                'Bank/Cash' as payment_mode,
                l.principal_amount as amount,
                'Loan Disbursal @ ' || l.annual_interest_rate || '% p.a. - ' || COALESCE(l.notes, '') as notes,
                l.created_at
            FROM chit_loans l
            JOIN chit_members m ON l.member_id = m.id
            WHERE 1=1 {date_cond_loan}

            ORDER BY tx_date DESC, created_at DESC
            LIMIT 120;
        """
        cur.execute(ledger_sql)
        ledger_rows = cur.fetchall()

        ledger = []
        for r in ledger_rows:
            ledger.append({
                'id': r[0],
                'date': str(r[1]),
                'type': r[2],
                'party_name': r[3],
                'chit_name': r[4],
                'ref_no': r[5],
                'payment_mode': r[6],
                'amount': float(r[7] or 0),
                'notes': r[8]
            })

        cur.execute("SELECT id, name FROM chit_groups WHERE deleted_at IS NULL ORDER BY name ASC;")
        schemes_list = [{'id': str(r[0]), 'name': r[1]} for r in cur.fetchall()]

        return jsonify({
            'success': True,
            'overview': {
                'total_inflow': total_inflow,
                'cash_inflow': cash_inflow,
                'bank_inflow': bank_inflow,
                'upi_inflow': upi_inflow,
                'total_outflow': total_outflow,
                'net_balance': net_balance,
                'foreman_earnings': foreman_earnings,
                'total_pending_dues': total_pending_dues,
                'active_groups_count': active_groups_count,
                'active_members_count': active_members_count,
                'active_loans_count': active_loans_count,
                'active_loans_principal': active_loans_principal,
                'total_loan_recovered': total_loan_recovered,
                'loan_interest_earned': loan_interest_earned,
                'loan_disbursed_outflow': loan_outflow,
                'credit_settled': chit_credit_settled
            },
            'forecast': forecast,
            'ledger': ledger,
            'schemes': schemes_list
        })
    except Exception as e:
        print(f"[WARN] get_accounting_overview: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# -------------------------------------------------------------
# REPORTS & STATEMENTS API
# -------------------------------------------------------------

@chit_bp.route('/api/reports/data', methods=['GET'])
def get_reports_data():
    rep_type = request.args.get('type', 'monthly').lower()
    chit_id = request.args.get('chit_id', 'all')
    month_idx = request.args.get('month_index', type=int)

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        if rep_type == 'monthly':
            # 1. Monthly Statement report for a specific chit & month
            target_chit_id = None
            if chit_id == 'all':
                cur.execute("SELECT id FROM chit_groups WHERE deleted_at IS NULL AND status = 'Active' ORDER BY name LIMIT 1;")
                first = cur.fetchone()
                if first: target_chit_id = str(first[0])
            else:
                target_chit_id = chit_id

            if not target_chit_id:
                return jsonify({'success': True, 'data': None})

            # Fetch chit info
            cur.execute("""
                SELECT id, name, chit_total_value, duration_months, current_month_index, monthly_installment, total_members
                FROM chit_groups WHERE id = %s;
            """, (target_chit_id,))
            g_row = cur.fetchone()
            if not g_row:
                return jsonify({'success': False, 'error': 'Chit group not found'}), 404

            c_dur = int(g_row[3] or 20)
            c_curr_m = month_idx or int(g_row[4] or 1)

            # Month details and schedule
            cur.execute("""
                SELECT s.amount_received, s.chit_loss, s.bonus, s.installment_kattubadi, s.payout_status, m.full_name, s.payout_date, s.month_year
                FROM chit_schedules s
                LEFT JOIN chit_memberships ms ON s.lifted_by_membership_id = ms.id
                LEFT JOIN chit_members m ON ms.member_id = m.id
                WHERE s.chit_group_id = %s AND s.month_index = %s;
            """, (target_chit_id, c_curr_m))
            sched = cur.fetchone()

            # Query all members who took payouts in this month
            cur.execute("""
                SELECT m.full_name
                FROM chit_memberships ms
                JOIN chit_members m ON ms.member_id = m.id
                WHERE ms.chit_group_id = %s AND ms.has_lifted = TRUE AND ms.lifted_month_index = %s;
            """, (target_chit_id, c_curr_m))
            monthly_winners = [w[0] for w in cur.fetchall()]
            winner_display = ", ".join(monthly_winners) if monthly_winners else (sched[5] if sched else None)

            # Installments per member for this month
            cur.execute("""
                SELECT 
                    m.full_name,
                    ms.account_number,
                    ms.ticket_number,
                    i.net_due_amount,
                    i.paid_amount,
                    i.pending_amount,
                    i.status,
                    i.month_year
                FROM chit_installments i
                JOIN chit_memberships ms ON i.membership_id = ms.id
                JOIN chit_members m ON ms.member_id = m.id
                WHERE i.chit_group_id = %s AND i.month_index = %s
                ORDER BY ms.ticket_number ASC, m.full_name ASC;
            """, (target_chit_id, c_curr_m))
            members_rows = cur.fetchall()

            members_list = []
            tot_expected = 0.0
            tot_collected = 0.0
            tot_pending = 0.0
            for idx, mr in enumerate(members_rows, 1):
                due_amt = float(mr[3] or 0)
                paid_amt = float(mr[4] or 0)
                pend_amt = float(mr[5] or 0)
                tot_expected += due_amt
                tot_collected += paid_amt
                tot_pending += pend_amt

                members_list.append({
                    'row_num': idx,
                    'member_name': mr[0],
                    'account_number': mr[1] or mr[2] or idx,
                    'due_amount': due_amt,
                    'paid_amount': paid_amt,
                    'pending_amount': pend_amt,
                    'status': 'Paid' if pend_amt <= 0 else ('Partial' if paid_amt > 0 else 'Pending')
                })

            col_pct = round((tot_collected / tot_expected * 100), 1) if tot_expected > 0 else 0

            return jsonify({
                'success': True,
                'data': {
                    'chit_id': target_chit_id,
                    'chit_name': g_row[1],
                    'chit_value': float(g_row[2] or 0),
                    'duration_months': c_dur,
                    'current_month_index': c_curr_m,
                    'month_year': sched[7] if sched else f"Month {c_curr_m}",
                    'expected_amount': tot_expected,
                    'collected_amount': tot_collected,
                    'pending_amount': tot_pending,
                    'collection_pct': col_pct,
                    'members': members_list,
                    'payout': {
                        'winner': winner_display,
                        'winners': monthly_winners,
                        'amount_received': float(sched[0] or 0) if sched else 0,
                        'payout_date': str(sched[6]) if sched and sched[6] else None,
                        'payout_status': sched[4] if sched else 'pending'
                    }
                }
            })

        elif rep_type == 'defaulters':
            # 2. Defaulters report across all active groups
            cur.execute("""
                SELECT 
                    m.id::text,
                    m.full_name,
                    m.phone,
                    m.customer_id,
                    COUNT(DISTINCT i.chit_group_id) as groups_count,
                    SUM(i.pending_amount) as total_pending
                FROM chit_installments i
                JOIN chit_memberships ms ON i.membership_id = ms.id
                JOIN chit_members m ON ms.member_id = m.id
                JOIN chit_groups g ON i.chit_group_id = g.id
                WHERE g.deleted_at IS NULL AND g.status = 'Active' AND i.pending_amount > 0
                GROUP BY m.id, m.full_name, m.phone, m.customer_id
                ORDER BY total_pending DESC;
            """)
            def_rows = cur.fetchall()
            defaulters = []
            for d in def_rows:
                defaulters.append({
                    'id': d[0],
                    'name': d[1],
                    'phone': d[2],
                    'customer_id': d[3],
                    'groups_count': d[4],
                    'total_pending': float(d[5] or 0)
                })
            return jsonify({'success': True, 'defaulters': defaulters})

        elif rep_type == 'earnings':
            # 3. Foreman Earnings report
            cur.execute("""
                SELECT id::text, name, chit_total_value, duration_months, current_month_index, foreman_monthly_earnings, commission_percent
                FROM chit_groups
                WHERE deleted_at IS NULL AND status = 'Active'
                ORDER BY name;
            """)
            earn_rows = cur.fetchall()
            earnings = []
            for er in earn_rows:
                e_monthly = float(er[5] or 0)
                e_curr_m = int(er[4] or 1)
                earnings.append({
                    'id': er[0],
                    'name': er[1],
                    'chit_value': float(er[2] or 0),
                    'duration_months': er[3],
                    'current_month': e_curr_m,
                    'monthly_earning': e_monthly,
                    'total_earned': e_monthly * e_curr_m
                })
            return jsonify({'success': True, 'earnings': earnings})

        elif rep_type == 'payouts':
            # 4. Payouts register - per subscriber payout
            cur.execute("""
                SELECT 
                    ms.id::text,
                    g.name,
                    ms.lifted_month_index,
                    s.month_year,
                    COALESCE(ms.payout_amount, s.amount_received * ms.share_units, 0),
                    COALESCE(ms.chit_loss, s.chit_loss * ms.share_units, 0),
                    COALESCE(ms.payout_date::text, s.payout_date::text, 'Scheduled'),
                    COALESCE(ms.payout_status, s.payout_status, 'paid'),
                    m.full_name,
                    ms.ticket_number,
                    COALESCE(ms.account_number, ms.ticket_number::text),
                    ms.share_units
                FROM chit_memberships ms
                JOIN chit_groups g ON ms.chit_group_id = g.id
                JOIN chit_members m ON ms.member_id = m.id
                LEFT JOIN chit_schedules s ON g.id = s.chit_group_id AND ms.lifted_month_index = s.month_index
                WHERE ms.has_lifted = TRUE AND ms.lifted_month_index IS NOT NULL AND g.deleted_at IS NULL
                ORDER BY COALESCE(ms.payout_date, s.payout_date) DESC NULLS LAST, ms.created_at DESC;
            """)
            pay_rows = cur.fetchall()
            payouts = []
            for pr in pay_rows:
                payouts.append({
                    'id': pr[0],
                    'chit_name': pr[1],
                    'month_index': pr[2],
                    'month_year': pr[3],
                    'amount_received': float(pr[4] or 0),
                    'chit_loss': float(pr[5] or 0),
                    'payout_date': pr[6] or 'Scheduled',
                    'status': pr[7] or 'Pending',
                    'winner': pr[8] or 'Not Assigned',
                    'ticket_number': pr[9],
                    'account_number': pr[10],
                    'share_units': float(pr[11] or 1.0)
                })
            return jsonify({'success': True, 'payouts': payouts})

        return jsonify({'success': False, 'error': 'Unknown report type'}), 400
    except Exception as e:
        print(f"[WARN] get_reports_data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# -------------------------------------------------------------
# RECEIPT DETAILS API
# -------------------------------------------------------------

@chit_bp.route('/api/receipts/payment/<payment_id>', methods=['GET'])
def get_payment_receipt_details(payment_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                p.id::text,
                COALESCE(p.receipt_no, 'RCP-' || SUBSTRING(p.id::text, 1, 6)) as receipt_no,
                p.payment_date::text,
                p.amount,
                p.payment_mode,
                COALESCE(m.full_name, 'Subscriber') as member_name,
                COALESCE(g.name, 'Chit Scheme') as chit_name,
                COALESCE(g.chit_total_value, 0) as chit_value,
                COALESCE(g.duration_months, 20) as duration_months,
                i.month_year,
                i.month_index,
                p.created_at::text,
                p.notes
            FROM chit_payments p
            LEFT JOIN chit_memberships ms ON p.membership_id = ms.id
            LEFT JOIN chit_members m ON ms.member_id = m.id
            LEFT JOIN chit_installments i ON p.installment_id = i.id
            LEFT JOIN chit_groups g ON i.chit_group_id = g.id
            WHERE p.id::text = %s;
        """, (payment_id,))
        r = cur.fetchone()
        if not r:
            return jsonify({'success': False, 'error': 'Receipt not found'}), 404

        return jsonify({
            'success': True,
            'receipt': {
                'id': r[0],
                'receipt_no': r[1],
                'payment_date': r[2],
                'amount': float(r[3] or 0),
                'payment_mode': r[4] or 'Cash',
                'member_name': r[5],
                'chit_name': r[6],
                'chit_value': float(r[7] or 0),
                'duration_months': r[8],
                'month_year': r[9] or f"Month {r[10]}",
                'month_index': r[10] or 1,
                'created_at': r[11],
                'notes': r[12] or '',
                'company_name': COMPANY_NAME
            }
        })
    except Exception as e:
        print(f"[WARN] get_payment_receipt_details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# -------------------------------------------------------------
# REST API ENDPOINTS
# -------------------------------------------------------------

@chit_bp.route('/api/company', methods=['GET'])
@chit_bp.route('/api/organization', methods=['GET'])
def get_company_info():
    return jsonify({
        'name': COMPANY_NAME,
        'short_name': 'Siva Durga',
        'currency': 'INR',
        'currency_symbol': CURRENCY_SYMBOL
    })

@chit_bp.route('/api/chitgroups', methods=['GET'])
def get_chit_groups():
    status_filter = request.args.get('status', 'active').lower()
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # 1. Compute aggregate header metrics across all active groups (Fresh cash only)
        cur.execute("""
            SELECT 
                COALESCE(SUM(p.amount), 0) as total_collected_this_month
            FROM chit_payments p
            WHERE date_trunc('month', p.payment_date) = date_trunc('month', CURRENT_DATE)
              AND LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment');
        """)
        collected_this_month = float(cur.fetchone()[0])

        cur.execute("""
            SELECT COUNT(*) 
            FROM chit_installments i
            JOIN chit_groups g ON i.chit_group_id = g.id
            WHERE g.deleted_at IS NULL AND g.status = 'Active' 
              AND i.month_index = g.current_month_index 
              AND i.pending_amount > 0;
        """)
        still_to_pay_count = int(cur.fetchone()[0])

        # Counts for tabs
        cur.execute("SELECT COUNT(*) FROM chit_groups WHERE deleted_at IS NULL AND status = 'Active';")
        active_count = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM chit_groups WHERE deleted_at IS NULL AND status = 'Draft';")
        draft_count = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM chit_groups WHERE deleted_at IS NULL;")
        all_count = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM chit_groups WHERE deleted_at IS NOT NULL;")
        trash_count = int(cur.fetchone()[0])

        # Filter query
        where_clause = "WHERE g.deleted_at IS NULL"
        if status_filter == 'active':
            where_clause += " AND g.status = 'Active'"
        elif status_filter == 'draft':
            where_clause += " AND g.status = 'Draft'"
        elif status_filter == 'trash':
            where_clause = "WHERE g.deleted_at IS NOT NULL"

        cur.execute(f"""
            SELECT 
                g.id, g.name, g.chit_total_value, g.duration_months,
                g.total_members, g.monthly_installment, g.commission_percent,
                g.foreman_monthly_earnings, g.start_month_year, g.current_month_index,
                g.status, g.schedule_type, g.is_month1_company_month, g.created_at,
                (SELECT COUNT(*) FROM chit_memberships m WHERE m.chit_group_id = g.id) as assigned_members_count,
                (SELECT COALESCE(SUM(share_units), 0) FROM chit_memberships m WHERE m.chit_group_id = g.id) as total_shares_assigned,
                (SELECT COALESCE(SUM(p.amount), 0) FROM chit_payments p JOIN chit_installments i ON p.installment_id = i.id WHERE i.chit_group_id = g.id AND LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment')) as total_collected,
                (SELECT COALESCE(SUM(p.amount), 0) FROM chit_payments p JOIN chit_installments i ON p.installment_id = i.id WHERE i.chit_group_id = g.id AND i.month_index = g.current_month_index AND LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment')) as current_month_collected,
                (SELECT COALESCE(SUM(p.amount), 0) FROM chit_payments p JOIN chit_installments i ON p.installment_id = i.id WHERE i.chit_group_id = g.id AND i.month_index = g.current_month_index AND LOWER(p.payment_mode) IN ('advance credit', 'credit settlement', 'credit adjustment')) as current_month_credit_settled,
                (SELECT COUNT(*) FROM chit_installments i WHERE i.chit_group_id = g.id AND i.month_index = g.current_month_index AND i.pending_amount <= 0.01) as current_month_paid_members,
                (SELECT installment_kattubadi FROM chit_schedules s WHERE s.chit_group_id = g.id AND s.month_index = g.current_month_index LIMIT 1) as current_month_target_kattubadi,
                (SELECT COALESCE(SUM(net_due_amount), 0) FROM chit_installments i WHERE i.chit_group_id = g.id AND i.month_index = g.current_month_index) as current_month_total_due,
                (SELECT COALESCE(SUM(s.amount_received * ms.share_units), 0) FROM chit_memberships ms JOIN chit_schedules s ON ms.chit_group_id = s.chit_group_id AND ms.lifted_month_index = s.month_index WHERE ms.chit_group_id = g.id AND ms.has_lifted = TRUE AND ms.lifted_month_index = g.current_month_index) as current_month_payout,
                (SELECT COALESCE(SUM(s.amount_received * ms.share_units), 0) FROM chit_memberships ms JOIN chit_schedules s ON ms.chit_group_id = s.chit_group_id AND ms.lifted_month_index = s.month_index WHERE ms.chit_group_id = g.id AND ms.has_lifted = TRUE AND ms.lifted_month_index IS NOT NULL) as total_payout
            FROM chit_groups g
            {where_clause}
            ORDER BY g.created_at DESC;
        """)
        rows = cur.fetchall()
        groups = []
        for r in rows:
            dur = int(r[3])
            val = float(r[2])
            tot_members = int(r[4])
            tot_shares = float(r[15])
            cur_m_idx = int(r[9])
            start_m_str = r[8]
            
            # Compute current month short name (e.g., 'Sep 26')
            cur_month_label = ''
            if start_m_str:
                try:
                    start_dt = datetime.strptime(str(start_m_str)[:7], "%Y-%m")
                    cur_m_dt = start_dt + relativedelta(months=cur_m_idx - 1)
                    cur_month_label = cur_m_dt.strftime("%b %y")
                except Exception:
                    cur_month_label = ''

            # Formatted created_at date (e.g. '14 Sept 2026, 9:11 am')
            created_at_fmt = ''
            if r[13]:
                # Format day Month Year, H:MM am/pm
                created_at_fmt = r[13].strftime("%d %B %Y, %I:%M %p").replace(" 0", " ")
                # Lowercase am/pm and match 'Sept'
                created_at_fmt = created_at_fmt.replace("September", "Sept").replace("AM", "am").replace("PM", "pm")

            kattubadi_single = float(r[20] or (val / dur))
            scheduled_dues = float(r[21])
            # If installments exist for current month, use their sum; otherwise calculate from assigned shares or total members
            cur_month_target = scheduled_dues if scheduled_dues > 0 else (kattubadi_single * (tot_shares if tot_shares > 0 else tot_members))
            groups.append({
                'id': str(r[0]),
                'name': r[1],
                'chit_total_value': val,
                'duration_months': dur,
                'total_members': tot_members,
                'monthly_installment': float(r[5]),
                'commission_percent': float(r[6] or 3.0),
                'foreman_monthly_earnings': float(r[7] or (val * 0.03)),
                'start_month_year': r[8],
                'current_month_index': cur_m_idx,
                'current_month_name': cur_month_label,
                'status': r[10],
                'schedule_type': r[11] or 'fixed',
                'is_month1_company_month': bool(r[12]),
                'created_at': created_at_fmt or (r[13].strftime("%d %b %Y, %I:%M %p") if r[13] else '—'),
                'assigned_members_count': int(r[14]),
                'total_shares_assigned': tot_shares,
                'open_shares_count': max(0.0, float(tot_members) - tot_shares),
                'total_collected': float(r[16]),
                'current_month_collected': float(r[17]),
                'current_month_credit_settled': float(r[18]),
                'current_month_paid_members': int(r[19]),
                'current_month_target': cur_month_target,
                'current_month_payout': float(r[22] or 0.0),
                'total_payout': float(r[23] or 0.0)
            })

        return jsonify({
            'total_collected_this_month': collected_this_month,
            'still_to_pay_count': still_to_pay_count,
            'counts': {
                'active': active_count,
                'draft': draft_count,
                'all': all_count,
                'trash': trash_count
            },
            'groups': groups
        })
    finally:
        cur.close()
        conn.close()


@chit_bp.route('/api/chitgroups/new', methods=['POST'])
def create_chit_group():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    chit_total_val = float(data.get('chit_total_value') or data.get('total_amount') or 5000.0)
    duration_months = int(data.get('duration_months') or data.get('total_months') or 20)
    assigned_members = data.get('members', [])
    total_members = int(data.get('total_members') or data.get('total_members_count') or len(assigned_members) or duration_months)
    commission_pct = float(data.get('commission_percent') or 3.0)
    start_month = str(data.get('start_month_year') or data.get('start_month') or datetime.now().strftime('%Y-%m'))[:7]
    status = data.get('status', 'Active')
    rules_notes = data.get('rules_notes', '')
    is_month1_company = bool(data.get('is_month1_company_month', False))

    if not name:
        name = f"Siva Durga {duration_months}M · ₹{int(chit_total_val):,} Chit"

    default_installment_type = (data.get('default_installment_type') or 'incremental').strip().lower()
    if default_installment_type not in ('fixed', 'incremental'):
        default_installment_type = 'incremental'

    base_installment = chit_total_val / float(duration_months)
    commission_amt = chit_total_val * (commission_pct / 100.0)

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO chit_groups (
                name, chit_total_value, duration_months, total_members,
                monthly_installment, commission_percent, foreman_commission_percent,
                foreman_monthly_earnings, start_month_year, current_month_index,
                status, schedule_type, rules_notes, is_month1_company_month,
                default_installment_type
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, 1,
                %s, 'fixed', %s, %s,
                %s
            ) RETURNING id;
        """, (
            name, chit_total_val, duration_months, total_members,
            base_installment, commission_pct, commission_pct,
            commission_amt, start_month, status, rules_notes, is_month1_company,
            default_installment_type
        ))
        group_id = cur.fetchone()[0]

        # Generate pre-calculated chart schedule
        schedule = ce.generate_chit_schedule(chit_total_val, duration_months, start_month, commission_pct, is_month1_company)
        for row in schedule:
            cur.execute("""
                INSERT INTO chit_schedules (
                    chit_group_id, month_index, month_year, chit_loss,
                    amount_received, bonus, installment_kattubadi, status, is_company_month
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                group_id, row['month_index'], row['month_year'],
                row['chit_loss'], row['amount_received'], row['bonus'],
                row['installment_kattubadi'], 'Open', row.get('is_company_month', False)
            ))

        # Enroll members if passed from Step 2
        t_num = 1
        account_nos_seen = {}
        for m in assigned_members:
            m_id = m.get('member_id')
            share = float(m.get('share_units') or m.get('shares_count') or 1.0)
            member_name = (m.get('full_name') or m.get('name') or '').strip()
            raw_acc = str(m.get('account_number') or '').strip()
            m_inst_type = (m.get('installment_type') or default_installment_type or 'incremental').strip().lower()
            if m_inst_type not in ('fixed', 'incremental'):
                m_inst_type = 'incremental'

            if not raw_acc:
                conn.rollback()
                return jsonify({'error': f"Subscriber '{member_name or t_num}' is missing an Account Number."}), 400
            
            if raw_acc in account_nos_seen:
                conn.rollback()
                return jsonify({'error': f"Account number '{raw_acc}' is repeated. Inside any particular group, the account number must be unique."}), 400
            account_nos_seen[raw_acc] = m_id or member_name

            if not m_id and member_name:
                # Quick-create member if new with unique 5-digit customer_id
                cur.execute("SELECT COALESCE(MAX(customer_id::integer), 10000) + 1 FROM chit_members WHERE customer_id ~ '^[0-9]{5}$';")
                next_cid = f"{(cur.fetchone()[0] or 10001):05d}"
                cur.execute("""
                    INSERT INTO chit_members (customer_id, full_name, phone, member_portal_enabled)
                    VALUES (%s, %s, %s, TRUE) RETURNING id;
                """, (next_cid, member_name, m.get('phone', '')))
                m_id = cur.fetchone()[0]

            if m_id:
                try:
                    ticket_val = int(raw_acc)
                except Exception:
                    ticket_val = t_num

                cur.execute("""
                    INSERT INTO chit_memberships (chit_group_id, member_id, ticket_number, account_number, share_units, has_lifted, installment_type)
                    VALUES (%s, %s, %s, %s, %s, FALSE, %s)
                    RETURNING id;
                """, (group_id, m_id, ticket_val, raw_acc, share, m_inst_type))
                ms_id = cur.fetchone()[0]

                # Create Month 1 installment scaled by share multiplier & installment type
                m1_info = schedule[0]
                if m_inst_type == 'fixed':
                    fixed_base = ce.get_fixed_installment_amount(chit_total_val, duration_months)
                    kattubadi = round_curr(fixed_base * share)
                    gross = round_curr((chit_total_val / float(duration_months)) * share)
                    bonus = round_curr(gross - kattubadi)
                else:
                    kattubadi = round_curr(float(m1_info['installment_kattubadi']) * share)
                    bonus = round_curr(float(m1_info['bonus']) * share)
                    gross = round_curr(kattubadi + bonus)

                cur.execute("""
                    INSERT INTO chit_installments (
                        chit_group_id, membership_id, month_index, month_year,
                        gross_amount, dividend_discount, net_due_amount, paid_amount,
                        pending_amount, status, kattubadi_due, bonus_discount
                    ) VALUES (
                        %s, %s, 1, %s,
                        %s, %s, %s, 0.00,
                        %s, 'due', %s, %s
                    );
                """, (
                    group_id, ms_id, m1_info['month_year'],
                    gross, bonus, kattubadi,
                    kattubadi, kattubadi, bonus
                ))
                t_num += 1

        # Keep total_members in sync if assigned members count exceeds initial target
        if len(assigned_members) > total_members:
            cur.execute("UPDATE chit_groups SET total_members = %s WHERE id = %s;", (len(assigned_members), group_id))

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'Created new fixed chit scheme', 'chit_groups', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            str(group_id),
            json.dumps({'name': name, 'value': chit_total_val, 'months': duration_months, 'members': total_members})
        ))

        conn.commit()
        return jsonify({
            'success': True,
            'id': str(group_id),
            'name': name,
            'schedule_count': len(schedule)
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<group_id>/edit-details', methods=['GET'])
def get_chit_group_edit_details(group_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Group info
        cur.execute("""
            SELECT 
                id, name, chit_total_value, duration_months, total_members,
                monthly_installment, commission_percent, start_month_year,
                current_month_index, status, rules_notes, is_month1_company_month,
                created_at, COALESCE(default_installment_type, 'incremental') as default_installment_type
            FROM chit_groups
            WHERE id = %s;
        """, (group_id,))
        grow = cur.fetchone()
        if not grow:
            return jsonify({'error': 'Chit group not found'}), 404

        val = float(grow[2])
        dur = int(grow[3])
        tot_members = int(grow[4])

        # Assigned members & shares
        cur.execute("""
            SELECT 
                ms.id as membership_id, ms.member_id, ms.ticket_number,
                ms.share_units, ms.has_lifted, ms.lifted_month_index,
                ms.start_month_index, ms.is_pool_split,
                m.full_name, m.phone, m.email,
                COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                m.customer_id,
                COALESCE(ms.installment_type, 'incremental') as installment_type
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            WHERE ms.chit_group_id = %s
            ORDER BY ms.ticket_number ASC;
        """, (group_id,))
        mrows = cur.fetchall()

        members = []
        total_shares = 0.0
        for m in mrows:
            sh = float(m[3])
            total_shares += sh
            m_itype = m[13] or 'incremental'
            if m_itype == 'fixed':
                est_monthly = round_curr(sh * ce.get_fixed_installment_amount(val, dur))
            else:
                est_monthly = round_curr(sh * (val / dur))

            members.append({
                'membership_id': str(m[0]),
                'member_id': str(m[1]),
                'ticket_number': m[2],
                'share_units': sh,
                'has_lifted': bool(m[4]),
                'lifted_month_index': m[5],
                'start_month_index': m[6] or 1,
                'is_pool_split': bool(m[7]),
                'full_name': m[8],
                'phone': m[9] or 'No phone',
                'email': m[10] or '',
                'account_number': m[11],
                'customer_id': m[12] or '',
                'installment_type': m_itype,
                'estimated_monthly_payment': est_monthly,
                'max_win_amount': val
            })

        # Schedules
        cur.execute("""
            SELECT month_index, month_year, chit_loss, amount_received, bonus, installment_kattubadi, is_company_month
            FROM chit_schedules
            WHERE chit_group_id = %s
            ORDER BY month_index ASC;
        """, (group_id,))
        srows = cur.fetchall()
        schedule = []
        for s in srows:
            schedule.append({
                'month_index': s[0],
                'month_year': s[1],
                'chit_loss': float(s[2]),
                'amount_received': float(s[3]),
                'bonus': float(s[4]),
                'installment_kattubadi': float(s[5]),
                'is_company_month': bool(s[6])
            })

        # Calculate Margin Matrix
        margins = ce.calculate_monthly_margins(schedule, tot_members, chit_total_value=val)

        # Impact audit stats for Delete Modal
        cur.execute("SELECT COUNT(*) FROM chit_installments WHERE chit_group_id = %s;", (group_id,))
        month_records_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chit_payments p JOIN chit_installments i ON p.installment_id = i.id WHERE i.chit_group_id = %s;", (group_id,))
        payments_count = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(p.amount), 0) FROM chit_payments p JOIN chit_installments i ON p.installment_id = i.id WHERE i.chit_group_id = %s AND LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment');", (group_id,))
        collected_amount = float(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM chit_schedules WHERE chit_group_id = %s AND payout_status = 'paid';", (group_id,))
        lifts_count = cur.fetchone()[0]

        return jsonify({
            'success': True,
            'group': {
                'id': str(grow[0]),
                'name': grow[1],
                'chit_total_value': val,
                'duration_months': dur,
                'total_members': tot_members,
                'monthly_installment': float(grow[5]),
                'commission_percent': float(grow[6] or 3.0),
                'start_month_year': grow[7],
                'current_month_index': int(grow[8]),
                'status': grow[9],
                'rules_notes': grow[10] or '',
                'is_month1_company_month': bool(grow[11]),
                'created_at': grow[12].strftime("%d %b %Y, %I:%M %p") if grow[12] else '—',
                'default_installment_type': grow[13] or 'incremental',
                'fixed_installment_amount': ce.get_fixed_installment_amount(val, dur),
                'shares_assigned': total_shares,
                'shares_target': tot_members,
                'shares_matches': total_shares == float(tot_members)
            },
            'members': members,
            'schedule': schedule,
            'margins': margins,
            'impact_audit': {
                'members_count': len(members),
                'month_records_count': month_records_count,
                'payments_count': payments_count,
                'collected_amount': collected_amount,
                'lifts_count': lifts_count,
                'months_ratio': f"{grow[8]}/{dur}"
            }
        })
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<group_id>', methods=['PUT'])
def update_chit_group(group_id):
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    status = data.get('status', 'Active')
    start_month = (data.get('start_month_year') or '').strip()[:7] if data.get('start_month_year') else None
    rules_notes = data.get('rules_notes', '')
    is_month1_company = bool(data.get('is_month1_company_month', False))
    total_members = data.get('total_members')
    duration_months = data.get('duration_months')

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Check current group state
        cur.execute("""
            SELECT id, name, chit_total_value, duration_months, total_members,
                   commission_percent, start_month_year, is_month1_company_month,
                   default_installment_type
            FROM chit_groups WHERE id = %s;
        """, (group_id,))
        grow = cur.fetchone()
        if not grow:
            return jsonify({'error': 'Chit group not found'}), 404

        cur_name, chit_total_val, cur_dur, cur_members = grow[1], float(grow[2]), int(grow[3]), int(grow[4])
        comm_pct, cur_start_month, cur_co_m1 = float(grow[5] or 3.0), grow[6], bool(grow[7])

        # Check existing payments and lifts
        cur.execute("""
            SELECT COUNT(*) 
            FROM chit_payments p 
            JOIN chit_installments i ON p.installment_id = i.id 
            WHERE i.chit_group_id = %s;
        """, (group_id,))
        payments_count = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) 
            FROM chit_schedules 
            WHERE chit_group_id = %s AND (payout_status = 'paid' OR lifted_by_membership_id IS NOT NULL);
        """, (group_id,))
        lifts_count = cur.fetchone()[0]

        has_financial_activity = (payments_count > 0 or lifts_count > 0)

        target_duration = int(duration_months) if duration_months is not None else cur_dur
        target_start_month = start_month if start_month else cur_start_month

        duration_changed = (target_duration != cur_dur)
        start_month_changed = (target_start_month != cur_start_month)

        if has_financial_activity and (duration_changed or start_month_changed):
            return jsonify({
                'error': f"Cannot change start month or duration: this scheme already has {payments_count} recorded payment(s) and {lifts_count} prize lift(s). Historical schedule is protected."
            }), 400

        # Calculate monthly installment
        base_installment = chit_total_val / float(target_duration)

        # Update chit_groups
        cur.execute("""
            UPDATE chit_groups
            SET name = COALESCE(NULLIF(%s, ''), name),
                status = %s,
                start_month_year = COALESCE(%s, start_month_year),
                rules_notes = %s,
                is_month1_company_month = %s,
                total_members = COALESCE(%s, total_members),
                duration_months = %s,
                monthly_installment = %s
            WHERE id = %s;
        """, (
            name, status, target_start_month, rules_notes, is_month1_company,
            int(total_members) if total_members is not None else None,
            target_duration, base_installment,
            group_id
        ))

        # If fresh scheme and schedule timing/duration changed, safely synchronize chit_schedules & Month 1 installments
        if not has_financial_activity and (duration_changed or start_month_changed):
            new_schedule = ce.generate_chit_schedule(
                chit_total_val, target_duration, target_start_month, comm_pct, is_month1_company
            )

            # Upsert / sync chit_schedules
            for row in new_schedule:
                cur.execute("SELECT id FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s;", (group_id, row['month_index']))
                existing_s = cur.fetchone()
                if existing_s:
                    cur.execute("""
                        UPDATE chit_schedules
                        SET month_year = %s, chit_loss = %s, amount_received = %s,
                            bonus = %s, installment_kattubadi = %s, is_company_month = %s
                        WHERE id = %s;
                    """, (
                        row['month_year'], row['chit_loss'], row['amount_received'],
                        row['bonus'], row['installment_kattubadi'], row.get('is_company_month', False),
                        existing_s[0]
                    ))
                else:
                    cur.execute("""
                        INSERT INTO chit_schedules (
                            chit_group_id, month_index, month_year, chit_loss,
                            amount_received, bonus, installment_kattubadi, status, is_company_month
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'Open', %s);
                    """, (
                        group_id, row['month_index'], row['month_year'],
                        row['chit_loss'], row['amount_received'], row['bonus'],
                        row['installment_kattubadi'], row.get('is_company_month', False)
                    ))

            # Delete excess months if duration decreased
            cur.execute("""
                DELETE FROM chit_schedules 
                WHERE chit_group_id = %s AND month_index > %s;
            """, (group_id, target_duration))

            # Update Month 1 installments for enrolled members
            m1_row = new_schedule[0]
            cur.execute("""
                SELECT id, share_units, COALESCE(installment_type, 'incremental')
                FROM chit_memberships 
                WHERE chit_group_id = %s;
            """, (group_id,))
            memberships = cur.fetchall()

            for ms_id, sh_units, inst_type in memberships:
                sh = float(sh_units or 1.0)
                if inst_type == 'fixed':
                    fixed_base = ce.get_fixed_installment_amount(chit_total_val, target_duration)
                    katt = round(fixed_base * sh, 2)
                    gross = round((chit_total_val / float(target_duration)) * sh, 2)
                    bon = round(gross - katt, 2)
                else:
                    katt = round(float(m1_row['installment_kattubadi']) * sh, 2)
                    bon = round(float(m1_row['bonus']) * sh, 2)
                    gross = katt + bon

                cur.execute("""
                    UPDATE chit_installments
                    SET month_year = %s,
                        gross_amount = %s,
                        dividend_discount = %s,
                        net_due_amount = %s,
                        pending_amount = %s,
                        kattubadi_due = %s,
                        bonus_discount = %s
                    WHERE membership_id = %s AND month_index = 1 AND status != 'paid';
                """, (m1_row['month_year'], gross, bon, katt, katt, katt, bon, ms_id))

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'Updated chit group parameters', 'chit_groups', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            str(group_id),
            json.dumps({
                'name': name or cur_name,
                'status': status,
                'duration_months': target_duration,
                'start_month_year': target_start_month,
                'total_members': total_members
            })
        ))

        conn.commit()
        return jsonify({'success': True, 'id': str(group_id)})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<group_id>/duplicate', methods=['POST'])
def duplicate_chit_group(group_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT name, chit_total_value, duration_months, total_members, commission_percent, monthly_installment, is_month1_company_month FROM chit_groups WHERE id = %s;", (group_id,))
        grow = cur.fetchone()
        if not grow:
            return jsonify({'error': 'Source chit not found'}), 404

        new_name = f"{grow[0]} (Copy)"
        val = float(grow[1])
        dur = int(grow[2])
        comm = float(grow[4] or 3.0)
        is_co = bool(grow[6])
        start_m = datetime.now().strftime('%Y-%m')

        cur.execute("""
            INSERT INTO chit_groups (
                name, chit_total_value, duration_months, total_members,
                monthly_installment, commission_percent, foreman_commission_percent,
                foreman_monthly_earnings, start_month_year, current_month_index,
                status, schedule_type, is_month1_company_month
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, 1,
                'Draft', 'fixed', %s
            ) RETURNING id;
        """, (
            new_name, val, dur, dur,
            val / dur, comm, comm,
            val * (comm / 100.0), start_m, is_co
        ))
        new_id = cur.fetchone()[0]

        # Generate schedule
        schedule = ce.generate_chit_schedule(val, dur, start_m, comm, is_co)
        for row in schedule:
            cur.execute("""
                INSERT INTO chit_schedules (
                    chit_group_id, month_index, month_year, chit_loss,
                    amount_received, bonus, installment_kattubadi, status, is_company_month
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'Open', %s);
            """, (
                new_id, row['month_index'], row['month_year'],
                row['chit_loss'], row['amount_received'], row['bonus'],
                row['installment_kattubadi'], row.get('is_company_month', False)
            ))

        conn.commit()
        return jsonify({'success': True, 'new_id': str(new_id), 'name': new_name})
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/trash', methods=['GET'])
def get_trashed_groups():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, name, chit_total_value, duration_months, deleted_at, delete_reason
            FROM chit_groups
            WHERE deleted_at IS NOT NULL
            ORDER BY deleted_at DESC;
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                'id': str(r[0]),
                'name': r[1],
                'chit_total_value': float(r[2]),
                'duration_months': int(r[3]),
                'deleted_at': r[4].strftime("%d %b %Y, %I:%M %p") if r[4] else '—',
                'delete_reason': r[5] or 'Not specified'
            })
        return jsonify(result)
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<group_id>/trash', methods=['POST'])
def trash_chit_group(group_id):
    data = request.get_json() or {}
    reason = data.get('reason', '')
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE chit_groups
            SET deleted_at = CURRENT_TIMESTAMP,
                delete_reason = %s
            WHERE id = %s;
        """, (reason, group_id))

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'Moved chit group to trash', 'chit_groups', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            str(group_id),
            json.dumps({'reason': reason})
        ))

        conn.commit()
        return jsonify({'success': True, 'id': str(group_id)})
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<group_id>/restore', methods=['POST'])
def restore_chit_group(group_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE chit_groups
            SET deleted_at = NULL,
                delete_reason = NULL
            WHERE id = %s;
        """, (group_id,))

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'Restored chit group from trash', 'chit_groups', %s, '{}');
        """, (
            get_current_actor(),
            get_current_actor_role(),
            str(group_id)
        ))

        conn.commit()
        return jsonify({'success': True, 'id': str(group_id)})
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<group_id>/members/assign', methods=['POST'])
def update_group_members(group_id):
    data = request.get_json() or {}
    action = data.get('action') # 'add', 'update_share', 'remove', 'transfer'
    membership_id = data.get('membership_id')
    member_id = data.get('member_id')
    share_units = float(data.get('share_units') or 1.0)
    joins_from = int(data.get('start_month_index') or 1)

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        if action == 'add':
            raw_acc = str(data.get('account_number') or '').strip()
            if not raw_acc:
                cur.execute("SELECT COALESCE(MAX(ticket_number), 0) + 1 FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
                raw_acc = str(cur.fetchone()[0])

            # Inside any particular group, the account number shouldn't repeat across different customers
            cur.execute("""
                SELECT member_id FROM chit_memberships 
                WHERE chit_group_id = %s AND account_number = %s
                LIMIT 1;
            """, (group_id, raw_acc))
            existing_acc = cur.fetchone()
            if existing_acc and (not member_id or str(existing_acc[0]) != str(member_id)):
                return jsonify({'error': f"Account number '{raw_acc}' is already in use by another subscriber in this group."}), 400

            if not member_id and data.get('new_member_name'):
                cur.execute("SELECT COALESCE(MAX(customer_id::integer), 10000) + 1 FROM chit_members WHERE customer_id ~ '^[0-9]{5}$';")
                next_cid = f"{(cur.fetchone()[0] or 10001):05d}"
                cur.execute("""
                    INSERT INTO chit_members (customer_id, full_name, phone, member_portal_enabled)
                    VALUES (%s, %s, %s, TRUE) RETURNING id;
                """, (next_cid, data['new_member_name'].strip(), data.get('new_member_phone', '').strip()))
                member_id = cur.fetchone()[0]

            if not member_id:
                return jsonify({'error': 'Member selection or new member name is required'}), 400

            try:
                ticket_val = int(raw_acc)
            except Exception:
                cur.execute("SELECT COALESCE(MAX(ticket_number), 0) + 1 FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
                ticket_val = cur.fetchone()[0]

            inst_type = (data.get('installment_type') or 'incremental').strip().lower()
            if inst_type not in ('fixed', 'incremental'):
                inst_type = 'incremental'

            cur.execute("""
                INSERT INTO chit_memberships (chit_group_id, member_id, ticket_number, account_number, share_units, start_month_index, installment_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (group_id, member_id, ticket_val, raw_acc, share_units, joins_from, inst_type))
            ms_id = cur.fetchone()[0]

            # Generate month installment if group is active
            cur.execute("SELECT current_month_index, duration_months, chit_total_value FROM chit_groups WHERE id = %s;", (group_id,))
            grow = cur.fetchone()
            if grow:
                cur_m = grow[0]
                cur.execute("SELECT month_year, installment_kattubadi, bonus FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s;", (group_id, cur_m))
                srow = cur.fetchone()
                if srow:
                    if inst_type == 'fixed':
                        fixed_base = ce.get_fixed_installment_amount(grow[2], grow[1])
                        katt = round_curr(fixed_base * share_units)
                        gross = round_curr((float(grow[2]) / float(grow[1])) * share_units)
                        bon = round_curr(gross - katt)
                    else:
                        katt = round_curr(float(srow[1]) * share_units)
                        bon = round_curr(float(srow[2]) * share_units)
                        gross = round_curr(katt + bon)

                    cur.execute("""
                        INSERT INTO chit_installments (
                            chit_group_id, membership_id, month_index, month_year,
                            gross_amount, dividend_discount, net_due_amount, paid_amount,
                            pending_amount, status, kattubadi_due, bonus_discount
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, 0.00,
                            %s, 'due', %s, %s
                        );
                    """, (group_id, ms_id, cur_m, srow[0], gross, bon, katt, katt, katt, bon))

            # Sync total_members if enrolled count now exceeds existing target
            cur.execute("""
                UPDATE chit_groups
                SET total_members = GREATEST(total_members, (SELECT COUNT(*) FROM chit_memberships WHERE chit_group_id = %s))
                WHERE id = %s;
            """, (group_id, group_id))

        elif action == 'toggle_member' and member_id:
            cur.execute("SELECT id FROM chit_memberships WHERE chit_group_id = %s AND member_id = %s;", (group_id, member_id))
            existing_ms = cur.fetchone()
            if existing_ms:
                # Member is enrolled -> check if any payments made
                ms_id = existing_ms[0]
                cur.execute("SELECT COUNT(*) FROM chit_payments p JOIN chit_installments i ON p.installment_id = i.id WHERE i.membership_id = %s;", (ms_id,))
                p_cnt = cur.fetchone()[0]
                if p_cnt > 0:
                    return jsonify({'error': 'Cannot unenroll subscriber: they already have recorded payments.'}), 400
                cur.execute("DELETE FROM chit_installments WHERE membership_id = %s AND chit_group_id = %s;", (ms_id, group_id))
                cur.execute("DELETE FROM chit_memberships WHERE id = %s;", (ms_id,))
                conn.commit()
                return jsonify({'success': True, 'enrolled': False})
            else:
                # Member is not enrolled -> enroll with next sequential account number
                cur.execute("SELECT account_number FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
                existing_accs = set(str(r[0]).strip() for r in cur.fetchall() if r[0])
                next_n = 1
                while str(next_n) in existing_accs:
                    next_n += 1
                raw_acc = str(next_n)

                cur.execute("SELECT current_month_index, duration_months, chit_total_value, COALESCE(default_installment_type, 'incremental') FROM chit_groups WHERE id = %s;", (group_id,))
                grow = cur.fetchone()
                if not grow:
                    return jsonify({'error': 'Chit group not found'}), 404
                cur_m, dur, g_val, def_itype = grow[0], grow[1], float(grow[2]), grow[3]

                inst_type = (data.get('installment_type') or def_itype or 'incremental').strip().lower()

                try:
                    ticket_val = int(raw_acc)
                except Exception:
                    cur.execute("SELECT COALESCE(MAX(ticket_number), 0) + 1 FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
                    ticket_val = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO chit_memberships (chit_group_id, member_id, ticket_number, account_number, share_units, start_month_index, installment_type)
                    VALUES (%s, %s, %s, %s, 1.0, 1, %s)
                    RETURNING id;
                """, (group_id, member_id, ticket_val, raw_acc, inst_type))
                ms_id = cur.fetchone()[0]

                cur.execute("SELECT month_year, installment_kattubadi, bonus FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s;", (group_id, cur_m))
                srow = cur.fetchone()
                if srow:
                    if inst_type == 'fixed':
                        fixed_base = ce.get_fixed_installment_amount(g_val, dur)
                        katt = round(fixed_base, 2)
                        gross = round(g_val / float(dur), 2)
                        bon = round(gross - katt, 2)
                    else:
                        katt = round(float(srow[1]), 2)
                        bon = round(float(srow[2]), 2)
                        gross = katt + bon

                    cur.execute("""
                        INSERT INTO chit_installments (
                            chit_group_id, membership_id, month_index, month_year,
                            gross_amount, dividend_discount, net_due_amount, paid_amount,
                            pending_amount, status, kattubadi_due, bonus_discount
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, 0.00,
                            %s, 'due', %s, %s
                        );
                    """, (group_id, ms_id, cur_m, srow[0], gross, bon, katt, katt, katt, bon))

                cur.execute("""
                    UPDATE chit_groups
                    SET total_members = GREATEST(total_members, (SELECT COUNT(*) FROM chit_memberships WHERE chit_group_id = %s))
                    WHERE id = %s;
                """, (group_id, group_id))

                conn.commit()
                return jsonify({'success': True, 'enrolled': True, 'account_number': raw_acc})

        elif action == 'quick_add_members':
            new_members = data.get('members') or []
            if not new_members:
                return jsonify({'error': 'No members provided'}), 400

            cur.execute("SELECT current_month_index, duration_months, chit_total_value, COALESCE(default_installment_type, 'incremental') FROM chit_groups WHERE id = %s;", (group_id,))
            grow = cur.fetchone()
            if not grow:
                return jsonify({'error': 'Chit group not found'}), 404
            cur_m, dur, g_val, def_itype = grow[0], grow[1], float(grow[2]), grow[3]

            cur.execute("SELECT month_year, installment_kattubadi, bonus FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s;", (group_id, cur_m))
            srow = cur.fetchone()

            cur.execute("SELECT account_number FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
            existing_accs = set(str(r[0]).strip() for r in cur.fetchall() if r[0])

            created_count = 0
            for m in new_members:
                member_name = (m.get('full_name') or m.get('name') or '').strip()
                if not member_name:
                    continue
                phone = str(m.get('phone') or '').strip()
                raw_acc = str(m.get('account_number') or '').strip()
                share = float(m.get('share_units') or 1.0)
                m_inst = (m.get('installment_type') or def_itype or 'incremental').strip().lower()

                if not raw_acc:
                    n = 1
                    while str(n) in existing_accs:
                        n += 1
                    raw_acc = str(n)

                if raw_acc in existing_accs:
                    conn.rollback()
                    return jsonify({'error': f"Account number '{raw_acc}' is already in use in this group."}), 400
                existing_accs.add(raw_acc)

                # Create member in chit_members
                cur.execute("SELECT COALESCE(MAX(customer_id::integer), 10000) + 1 FROM chit_members WHERE customer_id ~ '^[0-9]{5}$';")
                next_cid = f"{(cur.fetchone()[0] or 10001):05d}"
                cur.execute("""
                    INSERT INTO chit_members (customer_id, full_name, phone, member_portal_enabled)
                    VALUES (%s, %s, %s, TRUE) RETURNING id;
                """, (next_cid, member_name, phone))
                new_m_id = cur.fetchone()[0]

                try:
                    ticket_val = int(raw_acc)
                except Exception:
                    cur.execute("SELECT COALESCE(MAX(ticket_number), 0) + 1 FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
                    ticket_val = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO chit_memberships (chit_group_id, member_id, ticket_number, account_number, share_units, start_month_index, installment_type)
                    VALUES (%s, %s, %s, %s, %s, 1, %s)
                    RETURNING id;
                """, (group_id, new_m_id, ticket_val, raw_acc, share, m_inst))
                ms_id = cur.fetchone()[0]

                if srow:
                    if m_inst == 'fixed':
                        fixed_base = ce.get_fixed_installment_amount(g_val, dur)
                        katt = round(fixed_base * share, 2)
                        gross = round((g_val / float(dur)) * share, 2)
                        bon = round(gross - katt, 2)
                    else:
                        katt = round(float(srow[1]) * share, 2)
                        bon = round(float(srow[2]) * share, 2)
                        gross = katt + bon

                    cur.execute("""
                        INSERT INTO chit_installments (
                            chit_group_id, membership_id, month_index, month_year,
                            gross_amount, dividend_discount, net_due_amount, paid_amount,
                            pending_amount, status, kattubadi_due, bonus_discount
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, 0.00,
                            %s, 'due', %s, %s
                        );
                    """, (group_id, ms_id, cur_m, srow[0], gross, bon, katt, katt, katt, bon))
                created_count += 1

            cur.execute("""
                UPDATE chit_groups
                SET total_members = GREATEST(total_members, (SELECT COUNT(*) FROM chit_memberships WHERE chit_group_id = %s))
                WHERE id = %s;
            """, (group_id, group_id))

        elif action == 'batch_add':
            member_ids = data.get('member_ids') or []
            if not member_ids:
                return jsonify({'error': 'No member IDs provided'}), 400

            cur.execute("SELECT current_month_index, duration_months, chit_total_value, COALESCE(default_installment_type, 'incremental') FROM chit_groups WHERE id = %s;", (group_id,))
            grow = cur.fetchone()
            if not grow:
                return jsonify({'error': 'Chit group not found'}), 404
            cur_m, dur, g_val, def_itype = grow[0], grow[1], float(grow[2]), grow[3]

            cur.execute("SELECT month_year, installment_kattubadi, bonus FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s;", (group_id, cur_m))
            srow = cur.fetchone()

            cur.execute("SELECT account_number FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
            existing_accs = set(str(r[0]).strip() for r in cur.fetchall() if r[0])

            cur.execute("SELECT member_id FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
            enrolled_m_ids = set(str(r[0]) for r in cur.fetchall())

            next_acc_num = 1
            for mid in member_ids:
                mid_str = str(mid)
                if mid_str in enrolled_m_ids:
                    continue

                while str(next_acc_num) in existing_accs:
                    next_acc_num += 1
                raw_acc = str(next_acc_num)
                existing_accs.add(raw_acc)

                try:
                    ticket_val = int(raw_acc)
                except Exception:
                    cur.execute("SELECT COALESCE(MAX(ticket_number), 0) + 1 FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
                    ticket_val = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO chit_memberships (chit_group_id, member_id, ticket_number, account_number, share_units, start_month_index, installment_type)
                    VALUES (%s, %s, %s, %s, 1.0, 1, %s)
                    RETURNING id;
                """, (group_id, mid, ticket_val, raw_acc, def_itype))
                ms_id = cur.fetchone()[0]

                if srow:
                    if def_itype == 'fixed':
                        fixed_base = ce.get_fixed_installment_amount(g_val, dur)
                        katt = round(fixed_base, 2)
                        gross = round(g_val / float(dur), 2)
                        bon = round(gross - katt, 2)
                    else:
                        katt = round(float(srow[1]), 2)
                        bon = round(float(srow[2]), 2)
                        gross = katt + bon

                    cur.execute("""
                        INSERT INTO chit_installments (
                            chit_group_id, membership_id, month_index, month_year,
                            gross_amount, dividend_discount, net_due_amount, paid_amount,
                            pending_amount, status, kattubadi_due, bonus_discount
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, 0.00,
                            %s, 'due', %s, %s
                        );
                    """, (group_id, ms_id, cur_m, srow[0], gross, bon, katt, katt, katt, bon))
                enrolled_m_ids.add(mid_str)

            cur.execute("""
                UPDATE chit_groups
                SET total_members = GREATEST(total_members, (SELECT COUNT(*) FROM chit_memberships WHERE chit_group_id = %s))
                WHERE id = %s;
            """, (group_id, group_id))

        elif action == 'update_account_number' and membership_id:
            new_acc = str(data.get('account_number') or '').strip()
            if not new_acc:
                return jsonify({'error': 'Account number cannot be empty'}), 400
            cur.execute("SELECT member_id FROM chit_memberships WHERE id = %s;", (membership_id,))
            ms_m = cur.fetchone()
            if not ms_m:
                return jsonify({'error': 'Membership not found'}), 404
            cur.execute("""
                SELECT id FROM chit_memberships 
                WHERE chit_group_id = %s AND account_number = %s AND member_id != %s
                LIMIT 1;
            """, (group_id, new_acc, ms_m[0]))
            if cur.fetchone():
                return jsonify({'error': f"Account number '{new_acc}' is already in use by another subscriber in this group."}), 400
            cur.execute("UPDATE chit_memberships SET account_number = %s WHERE id = %s;", (new_acc, membership_id))

        elif action == 'update_share' and membership_id:
            cur.execute("""
                UPDATE chit_memberships
                SET share_units = %s, start_month_index = %s
                WHERE id = %s AND chit_group_id = %s;
            """, (share_units, joins_from, membership_id, group_id))

            # Recalculate base installment dues for ALL months for this membership based on new share_units
            cur.execute("SELECT current_month_index, duration_months, chit_total_value FROM chit_groups WHERE id = %s;", (group_id,))
            grow = cur.fetchone()
            if grow:
                cur_m, dur, g_val = grow[0], int(grow[1]), float(grow[2])
                cur.execute("SELECT member_id, COALESCE(installment_type, 'incremental') FROM chit_memberships WHERE id = %s;", (membership_id,))
                ms_info = cur.fetchone()
                m_member_id = ms_info[0] if ms_info else None
                ms_itype = ms_info[1] if ms_info else 'incremental'

                cur.execute("SELECT month_index, installment_kattubadi, bonus FROM chit_schedules WHERE chit_group_id = %s ORDER BY month_index ASC;", (group_id,))
                all_scheds = cur.fetchall()

                for srow in all_scheds:
                    mi_idx = srow[0]
                    if ms_itype == 'fixed':
                        fixed_base = ce.get_fixed_installment_amount(g_val, dur)
                        katt = round_curr(fixed_base * share_units)
                        gross = round_curr((g_val / float(dur)) * share_units)
                        bon = round_curr(gross - katt)
                    else:
                        katt = round_curr(float(srow[1] or 0.0) * share_units)
                        bon = round_curr(float(srow[2] or 0.0) * share_units)
                        gross = round_curr(katt + bon)

                    cur.execute("""
                        UPDATE chit_installments
                        SET gross_amount = %s,
                            dividend_discount = %s,
                            net_due_amount = %s,
                            kattubadi_due = %s,
                            bonus_discount = %s
                        WHERE membership_id = %s AND month_index = %s;
                    """, (gross, bon, katt, katt, bon, membership_id, mi_idx))

                if m_member_id:
                    rescale_and_rebalance_member_installments(cur, m_member_id, group_id)

        elif action == 'update_installment_type' and membership_id:
            new_inst_type = (data.get('installment_type') or 'incremental').strip().lower()
            if new_inst_type not in ('fixed', 'incremental'):
                new_inst_type = 'incremental'
            cur.execute("UPDATE chit_memberships SET installment_type = %s WHERE id = %s AND chit_group_id = %s;", (new_inst_type, membership_id, group_id))

            # Recalculate unpaid current month installment for this member
            cur.execute("SELECT current_month_index, duration_months, chit_total_value FROM chit_groups WHERE id = %s;", (group_id,))
            grow = cur.fetchone()
            if grow:
                cur_m, dur, g_val = grow[0], int(grow[1]), float(grow[2])
                cur.execute("SELECT share_units FROM chit_memberships WHERE id = %s;", (membership_id,))
                sh_row = cur.fetchone()
                sh = float(sh_row[0]) if sh_row else 1.0

                if new_inst_type == 'fixed':
                    fixed_base = ce.get_fixed_installment_amount(g_val, dur)
                    katt = round_curr(fixed_base * sh)
                    gross = round_curr((g_val / float(dur)) * sh)
                    bon = round_curr(gross - katt)
                else:
                    cur.execute("SELECT installment_kattubadi, bonus FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s;", (group_id, cur_m))
                    srow = cur.fetchone()
                    katt = round_curr(float(srow[0]) * sh) if srow else 0.0
                    bon = round_curr(float(srow[1]) * sh) if srow else 0.0
                    gross = round_curr(katt + bon)

                cur.execute("""
                    UPDATE chit_installments
                    SET gross_amount = %s,
                        dividend_discount = %s,
                        net_due_amount = %s,
                        pending_amount = %s - paid_amount,
                        kattubadi_due = %s,
                        bonus_discount = %s
                    WHERE membership_id = %s AND month_index = %s AND status != 'paid';
                """, (gross, bon, katt, katt, katt, bon, membership_id, cur_m))

        elif action == 'bulk_update_installment_type':
            new_inst_type = (data.get('installment_type') or 'incremental').strip().lower()
            if new_inst_type not in ('fixed', 'incremental'):
                new_inst_type = 'incremental'
            cur.execute("UPDATE chit_memberships SET installment_type = %s WHERE chit_group_id = %s;", (new_inst_type, group_id))
            cur.execute("UPDATE chit_groups SET default_installment_type = %s WHERE id = %s;", (new_inst_type, group_id))

            # Recalculate unpaid current month installments for all memberships in group
            cur.execute("SELECT current_month_index, duration_months, chit_total_value FROM chit_groups WHERE id = %s;", (group_id,))
            grow = cur.fetchone()
            if grow:
                cur_m, dur, g_val = grow[0], int(grow[1]), float(grow[2])
                cur.execute("SELECT installment_kattubadi, bonus FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s;", (group_id, cur_m))
                srow = cur.fetchone()
                cur.execute("SELECT id, share_units FROM chit_memberships WHERE chit_group_id = %s;", (group_id,))
                all_ms = cur.fetchall()
                for m_id_val, sh_val in all_ms:
                    sh = float(sh_val or 1.0)
                    if new_inst_type == 'fixed':
                        fixed_base = ce.get_fixed_installment_amount(g_val, dur)
                        katt = round_curr(fixed_base * sh)
                        gross = round_curr((g_val / float(dur)) * sh)
                        bon = round_curr(gross - katt)
                    else:
                        katt = round_curr(float(srow[0]) * sh) if srow else 0.0
                        bon = round_curr(float(srow[1]) * sh) if srow else 0.0
                        gross = round_curr(katt + bon)
                    cur.execute("""
                        UPDATE chit_installments
                        SET gross_amount = %s,
                            dividend_discount = %s,
                            net_due_amount = %s,
                            pending_amount = %s - paid_amount,
                            kattubadi_due = %s,
                            bonus_discount = %s
                        WHERE membership_id = %s AND month_index = %s AND status != 'paid';
                    """, (gross, bon, katt, katt, katt, bon, m_id_val, cur_m))

        elif action == 'remove' and membership_id:
            # Clean up any unpaid installments for this membership before removing
            cur.execute("DELETE FROM chit_payments WHERE installment_id IN (SELECT id FROM chit_installments WHERE membership_id = %s);", (membership_id,))
            cur.execute("DELETE FROM chit_installments WHERE membership_id = %s AND chit_group_id = %s;", (membership_id, group_id))
            cur.execute("DELETE FROM chit_memberships WHERE id = %s AND chit_group_id = %s;", (membership_id, group_id))

        elif action == 'transfer' and membership_id and data.get('target_member_id'):
            cur.execute("""
                UPDATE chit_memberships
                SET member_id = %s
                WHERE id = %s AND chit_group_id = %s;
            """, (data['target_member_id'], membership_id, group_id))

        conn.commit()
        return jsonify({'success': True})
    finally:
        cur.close()
        conn.close()

# -------------------------------------------------------------
# SCHEDULES & DUES ENDPOINTS
# -------------------------------------------------------------

@chit_bp.route('/api/chitgroups/<chit_id>/months', methods=['GET'])
def get_chit_months(chit_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT ms.lifted_month_index, m.full_name, ms.ticket_number
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            WHERE ms.chit_group_id = %s AND ms.has_lifted = TRUE AND ms.lifted_month_index IS NOT NULL;
        """, (chit_id,))
        lifted_rows = cur.fetchall()

        lifted_by_month = {}
        for lr in lifted_rows:
            m_i = int(lr[0])
            if m_i not in lifted_by_month:
                lifted_by_month[m_i] = []
            lifted_by_month[m_i].append({
                'name': lr[1],
                'ticket': lr[2]
            })

        cur.execute("""
            SELECT 
                s.id, s.month_index, s.month_year,
                s.chit_loss, s.amount_received, s.bonus, s.installment_kattubadi,
                s.lifted_by_membership_id, s.payout_date, s.payout_status, s.status,
                m.full_name as winner_name, ms.ticket_number as winner_ticket,
                s.is_company_month
            FROM chit_schedules s
            LEFT JOIN chit_memberships ms ON s.lifted_by_membership_id = ms.id
            LEFT JOIN chit_members m ON ms.member_id = m.id
            WHERE s.chit_group_id = %s
            ORDER BY s.month_index ASC;
        """, (chit_id,))
        rows = cur.fetchall()
        months = []
        for r in rows:
            m_idx = r[1]
            my = r[2]
            label = my
            try:
                dt = datetime.strptime(my, "%Y-%m")
                label = dt.strftime("%b %y")
            except Exception:
                pass

            m_winners = lifted_by_month.get(m_idx, [])
            w_name = ", ".join([w['name'] for w in m_winners]) if m_winners else r[11]
            w_ticket = ", ".join([str(w['ticket']) for w in m_winners]) if m_winners else r[12]

            months.append({
                'id': str(r[0]),
                'month_index': m_idx,
                'month_year': r[2],
                'month_label': f"{label} M{m_idx}",
                'chit_loss': float(r[3]),
                'amount_received': float(r[4]),
                'bonus': float(r[5]),
                'installment_kattubadi': float(r[6]),
                'lifted_by_membership_id': str(r[7]) if r[7] else None,
                'payout_date': r[8].isoformat() if r[8] else None,
                'payout_status': r[9],
                'status': r[10],
                'winner_name': w_name,
                'winner_ticket': w_ticket,
                'winners': [w['name'] for w in m_winners],
                'is_company_month': bool(r[13])
            })
        return jsonify(months)
    finally:
        cur.close()
        conn.close()

def rescale_and_rebalance_member_installments(cur, member_id, group_id=None):
    """
    For a given member (and optional group_id), rescales installments for all memberships,
    and proportionally splits historical paid_amount across split tickets so that 
    no false arrears or overpayments occur when multi-share memberships split.
    """
    where_sql = "WHERE member_id = %s"
    params = [member_id]
    if group_id:
        where_sql += " AND chit_group_id = %s"
        params.append(group_id)
        
    cur.execute(f"SELECT id, chit_group_id, ticket_number, share_units, COALESCE(installment_type, 'incremental'), COALESCE(has_lifted, FALSE), lifted_month_index FROM chit_memberships {where_sql};", tuple(params))
    ms_rows = cur.fetchall()
    if not ms_rows:
        return
        
    grouped = {}
    for ms_id, g_id, t_num, share, inst_type, has_lift, lift_m in ms_rows:
        key = (str(g_id), t_num)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append({
            'id': str(ms_id),
            'group_id': str(g_id),
            'ticket_number': t_num,
            'share_units': float(share or 1.0),
            'inst_type': inst_type,
            'has_lifted': bool(has_lift),
            'lifted_month_index': lift_m
        })
        
    for (g_id, t_num), siblings in grouped.items():
        total_ticket_shares = sum(s['share_units'] for s in siblings)
        if total_ticket_shares <= 0:
            continue
            
        cur.execute("SELECT chit_total_value, duration_months FROM chit_groups WHERE id = %s;", (g_id,))
        grow = cur.fetchone()
        if not grow:
            continue
        g_val = float(grow[0])
        duration = int(grow[1])
        
        cur.execute("SELECT month_index, month_year, installment_kattubadi, bonus FROM chit_schedules WHERE chit_group_id = %s ORDER BY month_index ASC;", (g_id,))
        s_rows = cur.fetchall()
        
        sib_ids = [s['id'] for s in siblings]
        
        for s in s_rows:
            m_idx, m_yr, katt_base, bonus_base = s
            katt_base = float(katt_base or 0.0)
            bonus_base = float(bonus_base or 0.0)
            
            cur.execute("SELECT COALESCE(SUM(paid_amount), 0) FROM chit_installments WHERE membership_id::text = ANY(%s) AND month_index = %s;", (sib_ids, m_idx))
            tot_paid_month = float(cur.fetchone()[0] or 0.0)

            cur.execute("""
                SELECT COALESCE(SUM(cp.amount), 0) 
                FROM chit_payments cp 
                JOIN chit_installments ci ON cp.installment_id = ci.id 
                WHERE ci.membership_id::text = ANY(%s) AND ci.month_index = %s;
            """, (sib_ids, m_idx))
            tot_payments_month = float(cur.fetchone()[0] or 0.0)
            
            # Calculate sibling net due amounts and direct payment records for month m_idx
            sib_info = []
            for sib in siblings:
                ms_id = sib['id']
                share = sib['share_units']
                inst_type = sib['inst_type']
                has_lift = sib['has_lifted']
                lift_m = sib['lifted_month_index']
                
                cur.execute("SELECT id, net_due_amount FROM chit_installments WHERE membership_id = %s AND month_index = %s;", (ms_id, m_idx))
                i_existing = cur.fetchone()
                
                is_lifted_in_m = has_lift and lift_m is not None and m_idx >= lift_m

                if inst_type == 'fixed':
                    fixed_base = ce.get_fixed_installment_amount(g_val, duration)
                    katt = round_curr(fixed_base * share)
                    gross = round_curr((g_val / float(duration)) * share)
                    bon = round_curr(gross - katt)
                else:
                    katt = round_curr(katt_base * share)
                    bon = round_curr(bonus_base * share)
                    gross = round_curr(katt + bon)
                    
                if is_lifted_in_m and i_existing and float(i_existing[1] or 0.0) > 0:
                    katt = float(i_existing[1])
                    
                sib_info.append({
                    'sib': sib,
                    'inst_id': str(i_existing[0]) if i_existing else None,
                    'gross': gross,
                    'bon': bon,
                    'katt': katt
                })
                
            tot_net_due = sum(item['katt'] for item in sib_info)
            
            direct_payments = {}
            for item in sib_info:
                inst_id = item['inst_id']
                d_paid = 0.0
                if inst_id:
                    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM chit_payments WHERE installment_id = %s;", (inst_id,))
                    d_paid = float(cur.fetchone()[0] or 0.0)
                direct_payments[item['sib']['id']] = d_paid
                
            tot_direct_payments = sum(direct_payments.values())
            tot_available = max(tot_direct_payments, tot_paid_month, tot_payments_month)

            # Check cumulative credit available prior to m_idx for these siblings across all prior cycles
            cur.execute("""
                SELECT 
                    COALESCE(SUM(ci.net_due_amount), 0) as prior_due,
                    COALESCE((
                        SELECT SUM(p.amount)
                        FROM chit_payments p
                        JOIN chit_installments pci ON p.installment_id = pci.id
                        WHERE pci.membership_id::text = ANY(%s)
                          AND pci.month_index < %s
                          AND LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment')
                    ), 0) as prior_paid
                FROM chit_installments ci
                WHERE ci.membership_id::text = ANY(%s)
                  AND ci.month_index < %s;
            """, (sib_ids, m_idx, sib_ids, m_idx))
            c_stat = cur.fetchone()
            c_due = float(c_stat[0] or 0.0) if c_stat else 0.0
            c_paid = float(c_stat[1] or 0.0) if c_stat else 0.0
            month_credit_avail = max(0.0, c_paid - c_due)

            rem_credit = month_credit_avail
            for item in sib_info:
                ms_id = item['sib']['id']
                share = item['sib']['share_units']
                katt = item['katt']
                gross = item['gross']
                bon = item['bon']
                
                if tot_available >= tot_net_due and tot_net_due > 0:
                    if len(sib_info) == 1:
                        sib_paid = tot_available
                    elif tot_direct_payments > 0 and all(direct_payments[s['sib']['id']] > 0 for s in sib_info):
                        sib_paid = direct_payments[ms_id]
                    else:
                        sib_paid = round_curr(tot_available * (katt / tot_net_due))
                elif tot_direct_payments > 0 and all(direct_payments[s['sib']['id']] <= s['katt'] for s in sib_info):
                    sib_paid = direct_payments[ms_id]
                elif tot_net_due > 0 and tot_available > 0:
                    sib_paid = round_curr(tot_available * (katt / tot_net_due))
                else:
                    ratio = share / total_ticket_shares
                    sib_paid = round_curr(tot_available * ratio)
                    
                # Do NOT auto-settle the installment with prior credit.
                # Prior credit remains unallocated surplus for the member to manually settle or roll over.
                pending = max(0.0, round_curr(katt - sib_paid))
                st = 'paid' if pending <= 0.01 else ('partial' if sib_paid > 0 else 'due')
                
                if item['inst_id']:
                    cur.execute("""
                        UPDATE chit_installments
                        SET gross_amount = %s,
                            dividend_discount = %s,
                            net_due_amount = %s,
                            kattubadi_due = %s,
                            bonus_discount = %s,
                            paid_amount = %s,
                            pending_amount = %s,
                            status = %s
                        WHERE id = %s;
                    """, (gross, bon, katt, katt, bon, sib_paid, pending, st, item['inst_id']))
                else:
                    cur.execute("""
                        INSERT INTO chit_installments (
                            chit_group_id, membership_id, month_index, month_year,
                            gross_amount, dividend_discount, net_due_amount, paid_amount,
                            pending_amount, status, kattubadi_due, bonus_discount
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s
                        );
                    """, (g_id, ms_id, m_idx, m_yr, gross, bon, katt, sib_paid, pending, st, katt, bon))

    # Sync member default status based on remaining unpaid closed installments
    cur.execute("""
        SELECT m.id, m.defaulted_manually,
               (
                   SELECT COUNT(*) 
                   FROM chit_installments ci
                   JOIN chit_schedules cs ON ci.chit_group_id = cs.chit_group_id AND ci.month_index = cs.month_index
                   JOIN chit_memberships cms ON ci.membership_id = cms.id
                   WHERE cms.member_id = m.id
                     AND cs.status = 'Closed'
                     AND ci.status = 'due'
                     AND ci.pending_amount > 0
               ) as missed_count
        FROM chit_members m
        WHERE m.id = %s;
    """, (member_id,))
    mrow = cur.fetchone()
    if mrow and not mrow[1]:
        missed_count = mrow[2] or 0
        if missed_count >= 3:
            cur.execute("UPDATE chit_members SET is_defaulted = TRUE, defaulted_reason = %s WHERE id = %s;", (f'Skipped {missed_count} repayments in closed cycles', member_id))
        else:
            cur.execute("UPDATE chit_members SET is_defaulted = FALSE, defaulted_reason = NULL, defaulted_at = NULL WHERE id = %s;", (member_id,))

def rescale_membership_installments(cur, membership_id):
    cur.execute("SELECT member_id, chit_group_id FROM chit_memberships WHERE id = %s;", (membership_id,))
    r = cur.fetchone()
    if r:
        rescale_and_rebalance_member_installments(cur, r[0], r[1])

def get_member_group_available_credit(cur, member_id, group_id):
    """
    Computes exact available advance credit for a member in a specific chit group:
    (Total fresh cash overpayments generated across all installments in this group)
    - (Total credit used via Advance Credit payments in this group)
    + (Transfers IN to this group from other chits)
    - (Transfers OUT of this group to other chits)
    """
    cur.execute("""
        SELECT i.id, i.month_index, i.net_due_amount,
               COALESCE(SUM(CASE WHEN LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment') THEN p.amount ELSE 0 END), 0) as cash_paid,
               COALESCE(SUM(CASE WHEN LOWER(p.payment_mode) IN ('advance credit', 'credit settlement', 'credit adjustment') THEN p.amount ELSE 0 END), 0) as credit_paid
        FROM chit_installments i
        JOIN chit_memberships ms ON i.membership_id = ms.id
        LEFT JOIN chit_payments p ON p.installment_id = i.id
        WHERE ms.member_id = %s AND ms.chit_group_id = %s
        GROUP BY i.id, i.month_index, i.net_due_amount
        ORDER BY i.month_index;
    """, (member_id, group_id))
    rows = cur.fetchall()

    tot_excess = 0.0
    tot_credit_used = 0.0
    for r in rows:
        net_due = float(r[2] or 0.0)
        cash_paid = float(r[3] or 0.0)
        credit_paid = float(r[4] or 0.0)

        cash_towards_due = min(cash_paid, max(0.0, net_due - credit_paid))
        excess = max(0.0, cash_paid - cash_towards_due)
        tot_excess += excess
        tot_credit_used += credit_paid

    # Transfers IN
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM chit_credit_transfers
        WHERE member_id = %s AND to_group_id = %s;
    """, (member_id, group_id))
    transfers_in = float(cur.fetchone()[0] or 0.0)

    # Transfers OUT
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM chit_credit_transfers
        WHERE member_id = %s AND from_group_id = %s;
    """, (member_id, group_id))
    transfers_out = float(cur.fetchone()[0] or 0.0)

    net_avail = max(0.0, round_curr(tot_excess - tot_credit_used + transfers_in - transfers_out))
    return net_avail

def get_member_credit_wallet(cur, member_id):
    """
    Returns complete credit wallet information for a subscriber:
    - total_available_credit: float
    - per_group: list of dicts with group details, available_credit, and pending_due
    - transfers: list of transfer history logs
    - credit_history: list of credit events (overpayments, settlements, transfers)
    """
    cur.execute("""
        SELECT DISTINCT g.id, g.name, g.chit_total_value, g.duration_months, g.current_month_index
        FROM chit_groups g
        JOIN chit_memberships ms ON ms.chit_group_id = g.id
        WHERE ms.member_id = %s AND g.deleted_at IS NULL
        ORDER BY g.name ASC;
    """, (member_id,))
    groups = cur.fetchall()

    per_group = []
    total_credit = 0.0
    for g in groups:
        g_id, g_name, g_val, g_dur, g_cur_m = g
        avail_c = get_member_group_available_credit(cur, member_id, g_id)
        total_credit += avail_c

        cur.execute("""
            SELECT COALESCE(SUM(i.pending_amount), 0)
            FROM chit_installments i
            JOIN chit_memberships ms ON i.membership_id = ms.id
            WHERE ms.member_id = %s AND ms.chit_group_id = %s;
        """, (member_id, g_id))
        pend_due = float(cur.fetchone()[0] or 0.0)

        per_group.append({
            'group_id': str(g_id),
            'group_name': g_name,
            'chit_total_value': float(g_val or 0.0),
            'duration_months': int(g_dur or 20),
            'current_month_index': int(g_cur_m or 1),
            'available_credit': avail_c,
            'pending_due': pend_due
        })

    cur.execute("""
        SELECT t.id, t.from_group_id, fg.name as from_group_name,
               t.to_group_id, tg.name as to_group_name,
               t.amount, t.notes, t.transferred_by, t.created_at
        FROM chit_credit_transfers t
        JOIN chit_groups fg ON t.from_group_id = fg.id
        JOIN chit_groups tg ON t.to_group_id = tg.id
        WHERE t.member_id = %s
        ORDER BY t.created_at DESC;
    """, (member_id,))
    t_rows = cur.fetchall()
    transfers = []
    for tr in t_rows:
        transfers.append({
            'id': str(tr[0]),
            'from_group_id': str(tr[1]),
            'from_group_name': tr[2],
            'to_group_id': str(tr[3]),
            'to_group_name': tr[4],
            'amount': float(tr[5]),
            'notes': tr[6] or '',
            'transferred_by': tr[7] or 'Admin',
            'created_at': tr[8].isoformat() if tr[8] else None,
            'date_formatted': tr[8].strftime("%d %b %Y, %I:%M %p") if tr[8] else ''
        })

    credit_events = []
    cur.execute("""
        SELECT p.id, p.amount, i.net_due_amount, p.payment_date, g.name, i.month_index, p.receipt_no
        FROM chit_payments p
        JOIN chit_installments i ON p.installment_id = i.id
        JOIN chit_memberships ms ON p.membership_id = ms.id
        JOIN chit_groups g ON i.chit_group_id = g.id
        WHERE ms.member_id = %s
          AND LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment')
          AND p.amount > i.net_due_amount
        ORDER BY p.payment_date DESC, p.created_at DESC;
    """, (member_id,))
    for er in cur.fetchall():
        p_amt = float(er[1])
        n_due = float(er[2] or 0.0)
        excess = max(0.0, round_curr(p_amt - n_due))
        if excess > 0:
            credit_events.append({
                'type': 'credit_added',
                'title': f'Advance Credit Generated (M{er[5]})',
                'amount': excess,
                'chit_name': er[4],
                'date': er[3].isoformat() if er[3] else None,
                'date_str': er[3].strftime("%d %b %Y") if er[3] else '',
                'notes': f"Overpayment on Month {er[5]} (Paid ₹{int(p_amt):,} vs Due ₹{int(n_due):,})",
                'receipt_no': er[6] or ''
            })

    cur.execute("""
        SELECT p.id, p.amount, p.payment_date, g.name, i.month_index, p.receipt_no
        FROM chit_payments p
        JOIN chit_installments i ON p.installment_id = i.id
        JOIN chit_memberships ms ON p.membership_id = ms.id
        JOIN chit_groups g ON i.chit_group_id = g.id
        WHERE ms.member_id = %s
          AND LOWER(p.payment_mode) IN ('advance credit', 'credit settlement', 'credit adjustment')
        ORDER BY p.payment_date DESC, p.created_at DESC;
    """, (member_id,))
    for sr in cur.fetchall():
        credit_events.append({
            'type': 'credit_settled',
            'title': f'Credit Settled (M{sr[4]})',
            'amount': float(sr[1]),
            'chit_name': sr[3],
            'date': sr[2].isoformat() if sr[2] else None,
            'date_str': sr[2].strftime("%d %b %Y") if sr[2] else '',
            'notes': f"Settled Month {sr[4]} due using advance credit",
            'receipt_no': sr[5] or ''
        })

    for tr in transfers:
        credit_events.append({
            'type': 'credit_transfer',
            'title': f"Shifted Credit: {tr['from_group_name']} → {tr['to_group_name']}",
            'amount': tr['amount'],
            'chit_name': f"{tr['from_group_name']} → {tr['to_group_name']}",
            'date': tr['created_at'][:10] if tr['created_at'] else None,
            'date_str': tr['date_formatted'],
            'notes': tr['notes'] or "Transferred credit across chit groups",
            'receipt_no': tr['id'][:8]
        })

    return {
        'total_available_credit': round_curr(total_credit),
        'per_group': per_group,
        'transfers': transfers,
        'credit_history': credit_events
    }

def ensure_group_month_installments(cur, group_id, month_index):
    cur.execute("""
        SELECT month_year, installment_kattubadi, bonus 
        FROM chit_schedules 
        WHERE chit_group_id = %s AND month_index = %s;
    """, (group_id, month_index))
    s_row = cur.fetchone()
    if not s_row:
        return
    m_yr, katt, bon = s_row
    katt = float(katt or 0.0)
    bon = float(bon or 0.0)

    cur.execute("SELECT chit_total_value, duration_months FROM chit_groups WHERE id = %s;", (group_id,))
    grow = cur.fetchone()
    g_val = float(grow[0]) if grow else 5000.0
    dur = int(grow[1]) if grow else 20

    cur.execute("""
        SELECT ms.id, ms.share_units, COALESCE(ms.installment_type, 'incremental')
        FROM chit_memberships ms
        WHERE ms.chit_group_id = %s
          AND ms.id NOT IN (
              SELECT i.membership_id FROM chit_installments i
              WHERE i.chit_group_id = %s AND i.month_index = %s
          );
    """, (group_id, group_id, month_index))
    missing = cur.fetchall()
    for ms_id, sh, inst_type in missing:
        share = float(sh or 1.0)
        if inst_type == 'fixed':
            fixed_base = ce.get_fixed_installment_amount(g_val, dur)
            net = round_curr(fixed_base * share)
            gross = round_curr((g_val / float(dur)) * share)
            b_disc = round_curr(gross - net)
        else:
            net = round_curr(katt * share)
            b_disc = round_curr(bon * share)
            gross = round_curr(net + b_disc)

        cur.execute("""
            INSERT INTO chit_installments (
                chit_group_id, membership_id, month_index, month_year,
                gross_amount, dividend_discount, net_due_amount, paid_amount,
                pending_amount, status, kattubadi_due, bonus_discount
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, 0.00,
                %s, 'due', %s, %s
            );
        """, (group_id, ms_id, month_index, m_yr, gross, b_disc, net, net, net, b_disc))

@chit_bp.route('/api/chitgroups/<chit_id>/month/<int:month_index>/dues', methods=['GET'])
def get_month_dues(chit_id, month_index):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        is_all = (chit_id == 'all')
        if is_all:
            cur.execute("SELECT id FROM chit_groups WHERE deleted_at IS NULL;")
            active_gids = [str(r[0]) for r in cur.fetchall()]
            for gid in active_gids:
                ensure_group_month_installments(cur, gid, month_index)
            conn.commit()

            cur.execute("""
                SELECT 
                    i.id as installment_id,
                    ms.id as membership_id,
                    ms.ticket_number,
                    ms.share_units,
                    m.id as member_id,
                    m.full_name,
                    m.phone,
                    i.gross_amount,
                    i.dividend_discount,
                    i.net_due_amount,
                    i.paid_amount,
                    i.pending_amount,
                    i.status,
                    (SELECT COUNT(*) FROM chit_payments p WHERE p.membership_id = ms.id) as payment_count,
                    ms.has_lifted,
                    ms.lifted_month_index,
                    g.name as chit_name,
                    g.id as group_id,
                    i.month_year,
                    COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                    m.customer_id,
                    COALESCE(ms.installment_type, 'incremental') as installment_type
                FROM chit_installments i
                JOIN chit_memberships ms ON i.membership_id = ms.id
                JOIN chit_members m ON ms.member_id = m.id
                JOIN chit_groups g ON i.chit_group_id = g.id
                WHERE i.month_index = %s AND g.deleted_at IS NULL
                ORDER BY g.name ASC, ms.ticket_number ASC;
            """, (month_index,))
            rows = cur.fetchall()

            sched_my = rows[0][18] if rows else ''
            sched_kattubadi = 0.0
            sched_bonus = 0.0
            sched_received = 0.0
            sched_loss = 0.0
            winner_name = None
            payout_status = 'pending'
            month_status = 'Open'
            is_co = False
        else:
            ensure_group_month_installments(cur, chit_id, month_index)
            conn.commit()

            cur.execute("""
                SELECT s.installment_kattubadi, s.bonus, s.amount_received, s.chit_loss, s.month_year,
                       m.full_name as winner_name, s.payout_status, s.status, s.is_company_month,
                       g.name as chit_name
                FROM chit_schedules s
                JOIN chit_groups g ON s.chit_group_id = g.id
                LEFT JOIN chit_memberships ms ON s.lifted_by_membership_id = ms.id
                LEFT JOIN chit_members m ON ms.member_id = m.id
                WHERE s.chit_group_id = %s AND s.month_index = %s;
            """, (chit_id, month_index))
            s_row = cur.fetchone()

            # Query all members who took payouts in this month
            cur.execute("""
                SELECT m.full_name
                FROM chit_memberships ms
                JOIN chit_members m ON ms.member_id = m.id
                WHERE ms.chit_group_id = %s AND ms.has_lifted = TRUE AND ms.lifted_month_index = %s;
            """, (chit_id, month_index))
            w_rows = cur.fetchall()
            winner_name = ", ".join([w[0] for w in w_rows]) if w_rows else (s_row[5] if s_row else None)

            sched_kattubadi = float(s_row[0]) if s_row else 0.0
            sched_bonus = float(s_row[1]) if s_row else 0.0
            sched_received = float(s_row[2]) if s_row else 0.0
            sched_loss = float(s_row[3]) if s_row else 0.0
            sched_my = s_row[4] if s_row else ''
            payout_status = s_row[6] if s_row else 'pending'
            month_status = s_row[7] if s_row else 'Open'
            is_co = bool(s_row[8]) if s_row else False
            g_name = s_row[9] if s_row else ''

            cur.execute("""
                SELECT 
                    i.id as installment_id,
                    ms.id as membership_id,
                    ms.ticket_number,
                    ms.share_units,
                    m.id as member_id,
                    m.full_name,
                    m.phone,
                    i.gross_amount,
                    i.dividend_discount,
                    i.net_due_amount,
                    i.paid_amount,
                    i.pending_amount,
                    i.status,
                    (SELECT COUNT(*) FROM chit_payments p WHERE p.membership_id = ms.id) as payment_count,
                    ms.has_lifted,
                    ms.lifted_month_index,
                    %s as chit_name,
                    i.chit_group_id as group_id,
                    i.month_year,
                    COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                    m.customer_id,
                    COALESCE(ms.installment_type, 'incremental') as installment_type
                FROM chit_installments i
                JOIN chit_memberships ms ON i.membership_id = ms.id
                JOIN chit_members m ON ms.member_id = m.id
                WHERE i.chit_group_id = %s AND i.month_index = %s
                ORDER BY ms.ticket_number ASC;
            """, (g_name, chit_id, month_index))
            rows = cur.fetchall()

        all_ms_ids = list({str(r[1]) for r in rows})
        all_member_ids = list({str(r[4]) for r in rows})

        # Batch 1: Query previous unpaid dues from prior months for all memberships
        arrears_by_ms = defaultdict(list)
        if all_ms_ids:
            cur.execute("""
                SELECT i.membership_id::text, i.id, i.month_index, i.month_year, i.pending_amount, s.month_year as sched_my, s.status as sched_status
                FROM chit_installments i
                JOIN chit_schedules s ON i.chit_group_id = s.chit_group_id AND i.month_index = s.month_index
                WHERE i.membership_id::text = ANY(%s)
                  AND i.month_index < %s 
                  AND i.pending_amount > 0
                ORDER BY i.month_index ASC;
            """, (all_ms_ids, month_index))
            for ar in cur.fetchall():
                arrears_by_ms[str(ar[0])].append(ar[1:])

        # Batch 2: Calculate available advance credit for all memberships/members in their chit group
        credits_by_ms = defaultdict(float)
        if all_member_ids:
            mem_group_credit = {}
            for r in rows:
                m_id_key = str(r[4])
                g_id_key = str(r[17])
                pair_key = (m_id_key, g_id_key)
                if pair_key not in mem_group_credit:
                    mem_group_credit[pair_key] = get_member_group_available_credit(cur, m_id_key, g_id_key)
                credits_by_ms[str(r[1])] = mem_group_credit[pair_key]

        # Batch 2b: Query payments broken down into fresh cash vs advance credit settlements
        inst_ids = [str(r[0]) for r in rows]
        actual_cash_by_inst = defaultdict(float)
        actual_credit_by_inst = defaultdict(float)
        actual_paid_by_inst = defaultdict(float)
        if inst_ids:
            cur.execute("""
                SELECT installment_id::text,
                       COALESCE(SUM(CASE WHEN LOWER(COALESCE(payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment') THEN amount ELSE 0 END), 0) as cash_amt,
                       COALESCE(SUM(CASE WHEN LOWER(payment_mode) IN ('advance credit', 'credit settlement', 'credit adjustment') THEN amount ELSE 0 END), 0) as credit_amt,
                       COALESCE(SUM(amount), 0) as total_amt
                FROM chit_payments
                WHERE installment_id::text = ANY(%s)
                GROUP BY installment_id;
            """, (inst_ids,))
            for pr in cur.fetchall():
                i_id_key = str(pr[0])
                actual_cash_by_inst[i_id_key] = float(pr[1] or 0.0)
                actual_credit_by_inst[i_id_key] = float(pr[2] or 0.0)
                actual_paid_by_inst[i_id_key] = float(pr[3] or 0.0)

        # Batch 3: Query defaulted status for all members
        default_status_by_member = {}
        if all_member_ids:
            cur.execute("""
                SELECT m.id::text, m.is_defaulted, m.defaulted_manually, m.defaulted_reason,
                       COALESCE(missed.cnt, 0) as total_missed_closed_all_groups
                FROM chit_members m
                LEFT JOIN (
                    SELECT cms.member_id, COUNT(*) as cnt
                    FROM chit_installments ci
                    JOIN chit_schedules cs ON ci.chit_group_id = cs.chit_group_id AND ci.month_index = cs.month_index
                    JOIN chit_memberships cms ON ci.membership_id = cms.id
                    WHERE cs.status = 'Closed'
                      AND ci.pending_amount > 0
                      AND cms.member_id::text = ANY(%s)
                    GROUP BY cms.member_id
                ) missed ON m.id = missed.member_id
                WHERE m.id::text = ANY(%s);
            """, (all_member_ids, all_member_ids))
            for dr in cur.fetchall():
                default_status_by_member[str(dr[0])] = (dr[1], dr[2], dr[3], dr[4])

        dues = []
        total_target = 0
        total_collected = 0       # Fresh cash collections only!
        total_credit_settled = 0  # Advance credit settlements
        total_dues_cleared = 0    # Net dues satisfied (by cash or credit)
        total_pending = 0
        total_arrears = 0
        total_excess_credit = 0
        paid_count = 0

        for r in rows:
            gross = float(r[7])
            net = float(r[9])
            inst_id_val = str(r[0])
            act_cash = actual_cash_by_inst.get(inst_id_val, 0.0)
            act_credit = actual_credit_by_inst.get(inst_id_val, 0.0)
            act_paid = actual_paid_by_inst.get(inst_id_val, 0.0)
            paid = max(float(r[10]), act_paid)
            pending = float(r[11])
            ms_id_val = str(r[1])
            member_id_val = str(r[4])

            # Excess cash generated that went into advance credit wallet
            excess_to_credit = max(0.0, round_curr(act_cash - net)) if act_cash > net else 0.0

            # Net dues satisfied on this installment (cannot exceed net due amount)
            cleared_on_inst = min(net, paid)

            # Sync legacy auto-credit zeroed installments back to unpaid state
            if float(r[10]) <= 0.01 and act_paid <= 0.01 and r[12] == 'paid' and net > 0:
                cur.execute("UPDATE chit_installments SET pending_amount = %s, status = 'due' WHERE id = %s;", (net, inst_id_val))
                pending = net
            elif float(r[10]) <= 0.01 and act_paid <= 0.01 and float(r[11]) < net and net > 0:
                cur.execute("UPDATE chit_installments SET pending_amount = %s WHERE id = %s;", (net, inst_id_val))
                pending = net

            # Look up previous unpaid dues from CLOSED months for this membership
            arrears_rows = arrears_by_ms.get(ms_id_val, [])
            prev_dues_amt = sum(float(ar[3] or 0.0) for ar in arrears_rows)
            missed_closed_months_count = len(arrears_rows)
            earliest_unpaid_my = arrears_rows[0][2] if arrears_rows else None
            due_since_str = format_month_year(earliest_unpaid_my) if earliest_unpaid_my else ''

            # Look up cumulative credit surplus across prior months for this membership
            avail_credit = credits_by_ms.get(ms_id_val, 0.0)
            credit_deduction = 0.0  # DO NOT auto-deduct credit; user will manually settle with credit or pay cash

            # Build detailed due breakdown
            breakdown = []
            for ar in arrears_rows:
                is_closed_sched = (len(ar) > 5 and ar[5] == 'Closed')
                breakdown.append({
                    'installment_id': str(ar[0]),
                    'month_index': ar[1],
                    'month_year': format_month_year(ar[2]) or f"Month {ar[1]}",
                    'amount': float(ar[3] or 0.0),
                    'is_closed': is_closed_sched,
                    'is_credit': False,
                    'tag': f"Arrear (M{ar[1]} · Closed)" if is_closed_sched else f"Arrear (M{ar[1]})"
                })
            cur_month_due = max(0.0, net - paid)
            if cur_month_due > 0:
                breakdown.append({
                    'installment_id': str(r[0]),
                    'month_index': month_index,
                    'month_year': format_month_year(r[18]) or f"Month {month_index}",
                    'amount': cur_month_due,
                    'is_closed': False,
                    'is_credit': False,
                    'tag': f"Current (M{month_index})"
                })
            if avail_credit > 0:
                breakdown.append({
                    'installment_id': str(r[0]),
                    'month_index': month_index,
                    'month_year': format_month_year(r[18]) or f"Month {month_index}",
                    'amount': avail_credit,
                    'is_closed': False,
                    'is_credit': True,
                    'tag': f"Available Credit (₹{int(avail_credit):,})"
                })

            # Check defaulted status across all groups for this member
            m_stat = default_status_by_member.get(member_id_val)
            is_def = False
            def_reason = ''
            if m_stat:
                m_is_def, m_man, m_reason, total_missed = m_stat
                total_missed = int(total_missed or 0)
                if m_man and m_is_def:
                    is_def = True
                    def_reason = m_reason or 'Marked manually by admin'
                elif total_missed >= 3:
                    is_def = True
                    def_reason = f'Skipped {total_missed} repayments in closed cycles'
                    if not m_is_def:
                        cur.execute("UPDATE chit_members SET is_defaulted = TRUE, defaulted_reason = %s, defaulted_at = NOW() WHERE id = %s;", (def_reason, member_id_val))
                        default_status_by_member[member_id_val] = (True, m_man, def_reason, total_missed)
                elif m_is_def and not m_man and total_missed < 3:
                    cur.execute("UPDATE chit_members SET is_defaulted = FALSE, defaulted_reason = NULL, defaulted_at = NULL WHERE id = %s;", (member_id_val,))
                    is_def = False
                    default_status_by_member[member_id_val] = (False, m_man, None, total_missed)

            cur_pending = max(0.0, net - paid)
            if cur_pending <= 0.01:
                cur_pending = 0.0
            total_member_pending = cur_pending + prev_dues_amt
            if total_member_pending <= 0.01:
                total_member_pending = 0.0

            total_target += max(0.0, (net + prev_dues_amt))
            total_collected += act_cash          # FRESH CASH ONLY!
            total_credit_settled += act_credit  # ADVANCE CREDIT SETTLED!
            total_dues_cleared += cleared_on_inst
            total_pending += total_member_pending
            total_arrears += prev_dues_amt
            total_excess_credit += excess_to_credit

            if total_member_pending <= 0.01 and (net + prev_dues_amt) > 0:
                paid_count += 1

            dues.append({
                'installment_id': str(r[0]),
                'membership_id': ms_id_val,
                'ticket_number': r[2],
                'account_number': r[19],
                'customer_id': r[20] or '',
                'share_units': float(r[3]),
                'installment_type': r[21] or 'incremental',
                'member_id': member_id_val,
                'member_name': r[5],
                'phone': r[6],
                'gross_amount': gross,
                'dividend_discount': float(r[8]),
                'net_due_amount': net,
                'paid_amount': paid,
                'cash_paid': act_cash,
                'credit_settled': act_credit,
                'excess_to_credit': excess_to_credit,
                'pending_amount': total_member_pending,
                'current_month_pending': cur_pending,
                'credit_deduction': 0.0,
                'available_credit': avail_credit,
                'status': 'paid' if total_member_pending <= 0.01 else ('partial' if paid > 0 else 'due'),
                'never_paid': r[13] == 0 and paid == 0,
                'has_lifted': bool(r[14]),
                'lifted_month_index': r[15],
                'chit_name': r[16] or '',
                'group_id': str(r[17]),
                'prev_dues': prev_dues_amt,
                'due_since': due_since_str,
                'due_breakdown': breakdown,
                'is_defaulted': is_def,
                'defaulted_reason': def_reason,
                'missed_closed_months_count': missed_closed_months_count
            })

        # Consolidate dues by (member_id, group_id) to ensure 1 tile per customer per group on Dashboard
        dues_by_key = {}
        for d in dues:
            key = (d['member_id'], d['group_id'])
            if key not in dues_by_key:
                dues_by_key[key] = {
                    'installment_id': d['installment_id'],
                    'membership_id': d['membership_id'],
                    'ticket_number': d['ticket_number'],
                    'account_number': d['account_number'],
                    'customer_id': d['customer_id'],
                    'share_units': d['share_units'],
                    'installment_type': d['installment_type'],
                    'member_id': d['member_id'],
                    'member_name': d['member_name'],
                    'phone': d['phone'],
                    'gross_amount': d['gross_amount'],
                    'dividend_discount': d['dividend_discount'],
                    'net_due_amount': d['net_due_amount'],
                    'paid_amount': d['paid_amount'],
                    'cash_paid': d['cash_paid'],
                    'credit_settled': d['credit_settled'],
                    'excess_to_credit': d['excess_to_credit'],
                    'pending_amount': d['pending_amount'],
                    'current_month_pending': d['current_month_pending'],
                    'credit_deduction': d['credit_deduction'],
                    'available_credit': d.get('available_credit', 0.0),
                    'never_paid': d['never_paid'],
                    'has_lifted': d['has_lifted'],
                    'lifted_month_index': d['lifted_month_index'],
                    'chit_name': d['chit_name'],
                    'group_id': d['group_id'],
                    'prev_dues': d['prev_dues'],
                    'due_since': d['due_since'],
                    'due_breakdown': list(d['due_breakdown']),
                    'is_defaulted': d['is_defaulted'],
                    'defaulted_reason': d['defaulted_reason'],
                    'missed_closed_months_count': d['missed_closed_months_count'],
                    'sub_tickets': [{
                        'membership_id': d['membership_id'],
                        'ticket_number': d['ticket_number'],
                        'account_number': d['account_number'],
                        'share_units': d['share_units'],
                        'has_lifted': d['has_lifted'],
                        'lifted_month_index': d['lifted_month_index'],
                        'net_due_amount': d['net_due_amount'],
                        'paid_amount': d['paid_amount'],
                        'cash_paid': d['cash_paid'],
                        'credit_settled': d['credit_settled'],
                        'excess_to_credit': d['excess_to_credit'],
                        'pending_amount': d['pending_amount'],
                        'credit_deduction': d['credit_deduction'],
                        'available_credit': d.get('available_credit', 0.0)
                    }]
                }
            else:
                existing = dues_by_key[key]
                existing['share_units'] = round_curr(existing['share_units'] + d['share_units'])
                existing['gross_amount'] = round_curr(existing['gross_amount'] + d['gross_amount'])
                existing['dividend_discount'] = round_curr(existing['dividend_discount'] + d['dividend_discount'])
                existing['net_due_amount'] = round_curr(existing['net_due_amount'] + d['net_due_amount'])
                existing['paid_amount'] = round_curr(existing['paid_amount'] + d['paid_amount'])
                existing['cash_paid'] = round_curr(existing.get('cash_paid', 0.0) + d['cash_paid'])
                existing['credit_settled'] = round_curr(existing.get('credit_settled', 0.0) + d['credit_settled'])
                existing['excess_to_credit'] = round_curr(existing.get('excess_to_credit', 0.0) + d['excess_to_credit'])
                existing['pending_amount'] = round_curr(existing['pending_amount'] + d['pending_amount'])
                existing['current_month_pending'] = round_curr(existing['current_month_pending'] + d['current_month_pending'])
                existing['credit_deduction'] = round_curr(existing.get('credit_deduction', 0.0) + d['credit_deduction'])
                existing['available_credit'] = round_curr(existing.get('available_credit', 0.0) + d.get('available_credit', 0.0))
                existing['prev_dues'] = round_curr(existing['prev_dues'] + d['prev_dues'])
                existing['has_lifted'] = existing['has_lifted'] or d['has_lifted']
                existing['never_paid'] = existing['never_paid'] and d['never_paid']
                existing['due_breakdown'].extend(d['due_breakdown'])
                existing['sub_tickets'].append({
                    'membership_id': d['membership_id'],
                    'ticket_number': d['ticket_number'],
                    'account_number': d['account_number'],
                    'share_units': d['share_units'],
                    'has_lifted': d['has_lifted'],
                    'lifted_month_index': d['lifted_month_index'],
                    'net_due_amount': d['net_due_amount'],
                    'paid_amount': d['paid_amount'],
                    'cash_paid': d['cash_paid'],
                    'credit_settled': d['credit_settled'],
                    'excess_to_credit': d['excess_to_credit'],
                    'pending_amount': d['pending_amount'],
                    'credit_deduction': d['credit_deduction'],
                    'available_credit': d.get('available_credit', 0.0)
                })

        consolidated_dues = list(dues_by_key.values())
        for cd in consolidated_dues:
            if cd['pending_amount'] <= 0.01:
                cd['pending_amount'] = 0.0
            if cd.get('current_month_pending', 0.0) <= 0.01:
                cd['current_month_pending'] = 0.0
            cd['status'] = 'paid' if cd['pending_amount'] <= 0.01 else ('partial' if cd['paid_amount'] > 0 else 'due')

        # Calculate defaulted count for this group view and system-wide
        if is_all:
            cur.execute("SELECT COUNT(*) FROM chit_members WHERE is_defaulted = TRUE;")
            defaulted_group_count = cur.fetchone()[0] or 0
        else:
            cur.execute("""
                SELECT COUNT(DISTINCT m.id)
                FROM chit_members m
                JOIN chit_memberships ms ON m.id = ms.member_id
                WHERE ms.chit_group_id = %s AND m.is_defaulted = TRUE;
            """, (chit_id,))
            defaulted_group_count = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM chit_members WHERE is_defaulted = TRUE;")
        defaulted_all_count = cur.fetchone()[0] or 0

        return jsonify({
            'month_index': month_index,
            'month_year': sched_my,
            'kattubadi_per_ticket': sched_kattubadi,
            'bonus_per_ticket': sched_bonus,
            'amount_received_if_lifted': sched_received,
            'chit_loss': sched_loss,
            'winner_name': winner_name,
            'payout_status': payout_status,
            'month_status': month_status,
            'is_company_month': is_co,
            'total_target': total_target,
            'total_collected': total_collected,
            'total_credit_settled': total_credit_settled,
            'total_dues_cleared': total_dues_cleared,
            'total_excess_credit': total_excess_credit,
            'total_pending': total_pending,
            'total_arrears': total_arrears,
            'defaulted_members_count': defaulted_group_count,
            'all_groups_defaulted_count': defaulted_all_count,
            'total_members': len(consolidated_dues),
            'paid_members_count': sum(1 for cd in consolidated_dues if cd['pending_amount'] <= 0.01),
            'unpaid_members_count': len(consolidated_dues) - sum(1 for cd in consolidated_dues if cd['pending_amount'] <= 0.01),
            'dues': consolidated_dues
        })
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<chit_id>/payouts-summary', methods=['GET'])
def get_chit_payouts_summary(chit_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, name, chit_total_value, duration_months, total_members, current_month_index, start_month_year
            FROM chit_groups
            WHERE id = %s;
        """, (chit_id,))
        grow = cur.fetchone()
        if not grow:
            return jsonify({'error': 'Chit group not found'}), 404

        g_id, name, val, dur, tot_m, cur_m, start_my = grow
        val = float(val or 0.0)
        dur = int(dur or 20)
        tot_m = int(tot_m or 20)
        cur_m = int(cur_m or 1)

        # All groups for tab switcher
        cur.execute("""
            SELECT id, name, chit_total_value, duration_months, current_month_index
            FROM chit_groups
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC;
        """)
        all_groups = [{
            'id': str(r[0]),
            'name': r[1],
            'chit_total_value': float(r[2] or 0),
            'duration_months': int(r[3] or 20),
            'current_month_index': int(r[4] or 1)
        } for r in cur.fetchall()]

        # Group rules and nominal base schedule for reference
        cur.execute("SELECT commission_percent, is_month1_company_month FROM chit_groups WHERE id = %s;", (chit_id,))
        g_comm_info = cur.fetchone()
        comm_pct = float(g_comm_info[0] or 3.0) if g_comm_info else 3.0
        is_co = bool(g_comm_info[1]) if g_comm_info else False
        base_sched = ce.generate_chit_schedule(val, dur, start_my, comm_pct, is_co)

        # Query all schedule rows for this group
        cur.execute("""
            SELECT 
                s.id, s.month_index, s.month_year,
                s.chit_loss, s.amount_received, s.bonus, s.installment_kattubadi,
                s.lifted_by_membership_id, s.payout_date, s.payout_status, s.status, s.notes,
                m.id as member_id, m.full_name, ms.ticket_number, m.phone, ms.share_units,
                s.is_company_month,
                COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                COALESCE(m.customer_id, '') as customer_id
            FROM chit_schedules s
            LEFT JOIN chit_memberships ms ON s.lifted_by_membership_id = ms.id
            LEFT JOIN chit_members m ON ms.member_id = m.id
            WHERE s.chit_group_id = %s
            ORDER BY s.month_index ASC;
        """, (chit_id,))
        rows = cur.fetchall()

        # Query unlifted sibling shares available for rebalancing
        cur.execute("""
            SELECT member_id, ticket_number, SUM(share_units)
            FROM chit_memberships
            WHERE chit_group_id = %s AND has_lifted = FALSE
            GROUP BY member_id, ticket_number;
        """, (chit_id,))
        unlifted_by_mem = {(str(r[0]), int(r[1])): float(r[2] or 0.0) for r in cur.fetchall()}

        # Query all memberships that have taken a payout in this group (including per-member payout columns)
        cur.execute("""
            SELECT ms.id, ms.lifted_month_index, ms.member_id, m.full_name, ms.ticket_number,
                   ms.share_units, m.phone,
                   COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                   COALESCE(m.customer_id, '') as customer_id,
                   ms.payout_date, ms.payout_status, ms.payout_notes, ms.payout_amount, ms.chit_loss
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            WHERE ms.chit_group_id = %s AND ms.has_lifted = TRUE AND ms.lifted_month_index IS NOT NULL
            ORDER BY ms.ticket_number ASC;
        """, (chit_id,))
        all_lifted_ms = cur.fetchall()

        lifted_by_month = {}
        for lm in all_lifted_ms:
            m_i = int(lm[1])
            if m_i not in lifted_by_month:
                lifted_by_month[m_i] = []
            lifted_by_month[m_i].append({
                'membership_id': str(lm[0]),
                'member_id': str(lm[2]),
                'name': lm[3],
                'ticket_number': lm[4],
                'share_units': float(lm[5] or 1.0),
                'phone': lm[6] or '',
                'account_number': lm[7],
                'customer_id': lm[8] or '',
                'payout_date': lm[9].isoformat() if lm[9] else None,
                'payout_status': (lm[10] or 'paid').lower() if lm[10] else None,
                'notes': lm[11] or '',
                'payout_amount': float(lm[12]) if lm[12] is not None else None,
                'chit_loss': float(lm[13]) if lm[13] is not None else None,
                'unlifted_shares': unlifted_by_mem.get((str(lm[2]), int(lm[4])), 0.0),
                'max_available_shares': float(lm[5] or 1.0) + unlifted_by_mem.get((str(lm[2]), int(lm[4])), 0.0)
            })

        months = []
        unpaid_payouts = []
        unpaid_total_amt = 0.0
        payouts_taken_count = 0
        raw_sched = []

        for r in rows:
            m_idx = r[1]
            my = r[2]
            label = my
            try:
                dt = datetime.strptime(my, "%Y-%m")
                label = dt.strftime("%b %y")
            except Exception:
                pass

            p_status = (r[9] or 'pending').lower()
            amt_rec = float(r[4] or 0.0)
            c_loss = float(r[3] or 0.0)
            bonus = float(r[5] or 0.0)
            kattubadi = float(r[6] or 0.0)

            # Ensure schedule amount_received & chit_loss match the 1.0x share nominal baseline
            if 1 <= m_idx <= len(base_sched):
                nom_base = base_sched[m_idx - 1]
                nom_amt = float(nom_base['amount_received'])
                nom_loss = float(nom_base['chit_loss'])
                # Self-heal any inflated / multiplied values in chit_schedules
                if amt_rec <= 0 or amt_rec > val or (nom_amt > 0 and amt_rec > nom_amt and round(amt_rec % nom_amt, 2) == 0):
                    amt_rec = nom_amt
                    c_loss = nom_loss
                    try:
                        cur.execute("UPDATE chit_schedules SET amount_received = %s, chit_loss = %s WHERE id = %s;", (nom_amt, nom_loss, r[0]))
                    except Exception:
                        pass

            raw_sched.append({
                'month_index': m_idx,
                'installment_kattubadi': kattubadi,
                'amount_received': amt_rec,
                'is_company_month': bool(r[17])
            })

            recipients_list = lifted_by_month.get(m_idx, [])
            if not recipients_list and r[7]:
                recipients_list = [{
                    'member_id': str(r[12]) if r[12] else None,
                    'membership_id': str(r[7]) if r[7] else None,
                    'name': r[13] or 'Subscriber',
                    'ticket_number': r[14],
                    'phone': r[15] or '',
                    'share_units': float(r[16] or 1.0),
                    'account_number': r[18],
                    'customer_id': r[19] or '',
                    'payout_date': r[8].isoformat() if r[8] else None,
                    'payout_status': p_status,
                    'notes': r[11] or '',
                    'payout_amount': round_curr(amt_rec * float(r[16] or 1.0)),
                    'chit_loss': round_curr(c_loss * float(r[16] or 1.0))
                }]

            # Populate per-recipient exact payout amounts and statuses
            for rec in recipients_list:
                if rec.get('payout_amount') is None:
                    rec['payout_amount'] = round_curr(amt_rec * rec['share_units'])
                if rec.get('chit_loss') is None:
                    rec['chit_loss'] = round_curr(c_loss * rec['share_units'])
                if not rec.get('payout_date'):
                    rec['payout_date'] = r[8].isoformat() if r[8] else None
                if not rec.get('payout_status'):
                    rec['payout_status'] = p_status if len(recipients_list) > 0 else 'none'
                if not rec.get('notes'):
                    rec['notes'] = r[11] or ''

            has_payout = len(recipients_list) > 0
            if has_payout:
                payouts_taken_count += len(recipients_list)
                for rec in recipients_list:
                    if rec['payout_status'] == 'unpaid':
                        unpaid_payouts.append({
                            'month_index': m_idx,
                            'month_year': my,
                            'amount': rec['payout_amount'],
                            'member_name': rec['name'],
                            'ticket_number': rec['ticket_number'],
                            'account_number': rec['account_number'],
                            'customer_id': rec['customer_id'],
                            'payout_date': rec['payout_date'],
                            'membership_id': rec['membership_id']
                        })
                        unpaid_total_amt += rec['payout_amount']

            month_payout_status = 'paid'
            if any(rec.get('payout_status') == 'unpaid' for rec in recipients_list) or p_status == 'unpaid':
                month_payout_status = 'unpaid'
            elif not has_payout:
                month_payout_status = 'none'

            months.append({
                'id': str(r[0]),
                'month_index': m_idx,
                'month_year': my,
                'month_label': f"{label} M{m_idx}",
                'month_name_short': label.split(' ')[0] if ' ' in label else label,
                'chit_loss': c_loss,
                'amount_received': amt_rec,
                'bonus': bonus,
                'installment_kattubadi': kattubadi,
                'has_payout': has_payout,
                'payout_status': month_payout_status,
                'payout_date': r[8].isoformat() if r[8] else None,
                'notes': r[11] or '',
                'recipient': recipients_list[0] if recipients_list else None,
                'recipients': recipients_list,
                'is_company_month': bool(r[17])
            })

        # Eligible members: enrolled in this chit but haven't taken payout yet
        cur.execute("""
            SELECT ms.id, ms.member_id, m.full_name, ms.ticket_number, ms.share_units, m.phone,
                   COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                   COALESCE(m.customer_id, '') as customer_id
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            WHERE ms.chit_group_id = %s AND (ms.has_lifted = FALSE OR ms.has_lifted IS NULL)
            ORDER BY ms.ticket_number ASC;
        """, (chit_id,))
        raw_eligible = cur.fetchall()
        member_ids = list({str(er[1]) for er in raw_eligible if er[1]})
        active_loans_by_member = {}
        if member_ids:
            cur.execute("""
                SELECT id::text, member_id::text, principal_amount, annual_interest_rate, disbursal_date,
                       total_repaid_principal, total_repaid_interest
                FROM chit_loans
                WHERE member_id::text = ANY(%s) AND status = 'active';
            """, (member_ids,))
            for lr in cur.fetchall():
                calc = calculate_loan_compound_interest(
                    principal=lr[2], annual_rate=lr[3], disbursal_date=lr[4],
                    repaid_principal=lr[5], repaid_interest=lr[6]
                )
                m_uid = lr[1]
                if m_uid not in active_loans_by_member:
                    active_loans_by_member[m_uid] = []
                active_loans_by_member[m_uid].append({
                    'id': lr[0],
                    'principal': float(lr[2] or 0),
                    'rate': float(lr[3] or 0),
                    'disbursal_date': str(lr[4]),
                    'remaining_principal': calc['remaining_principal'],
                    'accrued_interest': calc['accrued_interest'],
                    'total_payoff': calc['total_payoff']
                })

        eligible_members = [{
            'membership_id': str(er[0]),
            'member_id': str(er[1]),
            'full_name': er[2],
            'ticket_number': er[3],
            'share_units': float(er[4] or 1.0),
            'phone': er[5] or '',
            'account_number': er[6],
            'customer_id': er[7] or '',
            'active_loans': active_loans_by_member.get(str(er[1]), [])
        } for er in raw_eligible]

        # Actual enrolled members in this chit group
        cur.execute("SELECT COUNT(*) FROM chit_memberships WHERE chit_group_id = %s;", (chit_id,))
        enrolled_count = cur.fetchone()[0] or 0

        # Margin calculation via calc engine using actual enrolled members count
        margin_info = ce.calculate_monthly_margins(raw_sched, enrolled_count, chit_total_value=val)

        return jsonify({
            'success': True,
            'chit': {
                'id': str(g_id),
                'name': name,
                'chit_total_value': val,
                'duration_months': dur,
                'total_members': tot_m,
                'enrolled_members_count': enrolled_count,
                'current_month_index': cur_m,
                'start_month_year': start_my or ''
            },
            'all_groups': all_groups,
            'payouts_taken_count': payouts_taken_count,
            'total_shares_count': dur,
            'unpaid_payouts': unpaid_payouts,
            'unpaid_total_amount': unpaid_total_amt,
            'margin': margin_info,
            'months': months,
            'eligible_members': eligible_members
        })
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<chit_id>/month/<int:month_index>/payout', methods=['POST', 'PUT'])
def handle_month_payout(chit_id, month_index):
    data = request.get_json() or {}
    membership_id = data.get('membership_id')
    share_count = float(data.get('share_count') or data.get('payout_shares') or 1.0)
    payout_date = data.get('payout_date') or str(date.today())
    pay_now = bool(data.get('pay_now', True))
    payout_status = 'paid' if pay_now else 'unpaid'
    method = data.get('payment_mode') or 'Bank Transfer'
    notes = (data.get('notes') or '').strip()
    full_notes = f"{method} · {notes}" if notes else method

    if not membership_id:
        return jsonify({'error': 'Member ticket required to record payout'}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Check membership
        cur.execute("""
            SELECT ms.chit_group_id, ms.member_id, ms.ticket_number, ms.share_units, ms.has_lifted,
                   g.chit_total_value, g.duration_months, g.start_month_year, g.commission_percent, g.is_month1_company_month,
                   g.name as group_name, COALESCE(ms.account_number, ms.ticket_number::text) as account_number
            FROM chit_memberships ms
            JOIN chit_groups g ON ms.chit_group_id = g.id
            WHERE ms.id = %s;
        """, (membership_id,))
        ms_info = cur.fetchone()
        if not ms_info:
            return jsonify({'error': 'Membership not found'}), 404

        (ms_grp_id, m_id, t_num, orig_shares, has_lift,
         g_val, g_dur, g_start, g_comm, g_isco, g_name, acc_no) = ms_info
        orig_shares = float(orig_shares or 1.0)
        share_count = min(max(0.5, share_count), orig_shares)

        # Base schedule for 1 nominal chit
        base_sched = ce.generate_chit_schedule(float(g_val), int(g_dur or 20), g_start, float(g_comm or 3.0), bool(g_isco))
        if month_index < 1 or month_index > len(base_sched):
            return jsonify({'error': 'Invalid month index'}), 400
        
        m_base = base_sched[month_index - 1]
        calc_amt_rec = round_curr(float(m_base['amount_received']) * share_count)
        calc_loss = round_curr(float(m_base['chit_loss']) * share_count)

        # Multi-share split handling
        if share_count < orig_shares:
            rem_shares = round_curr(orig_shares - share_count)
            cur.execute("""
                SELECT id FROM chit_memberships
                WHERE chit_group_id = %s AND member_id = %s AND ticket_number = %s AND has_lifted = FALSE AND id != %s
                LIMIT 1;
            """, (chit_id, m_id, t_num, membership_id))
            sib = cur.fetchone()
            if sib:
                rem_ms_id = sib[0]
                cur.execute("UPDATE chit_memberships SET share_units = share_units + %s WHERE id = %s;", (rem_shares, rem_ms_id))
            else:
                cur.execute("""
                    INSERT INTO chit_memberships (chit_group_id, member_id, ticket_number, account_number, share_units, has_lifted)
                    VALUES (%s, %s, %s, %s, %s, FALSE)
                    RETURNING id;
                """, (chit_id, m_id, t_num, acc_no, rem_shares))
                rem_ms_id = cur.fetchone()[0]

            cur.execute("""
                UPDATE chit_memberships
                SET share_units = %s, has_lifted = TRUE, lifted_month_index = %s,
                    payout_date = %s, payout_status = %s, payout_notes = %s,
                    payout_amount = %s, chit_loss = %s
                WHERE id = %s;
            """, (share_count, month_index, payout_date, payout_status, full_notes, calc_amt_rec, calc_loss, membership_id))

            # Rescale and rebalance installment amounts & historical payments for split tickets
            rescale_and_rebalance_member_installments(cur, m_id, chit_id)
        else:
            cur.execute("""
                UPDATE chit_memberships
                SET has_lifted = TRUE, lifted_month_index = %s,
                    payout_date = %s, payout_status = %s, payout_notes = %s,
                    payout_amount = %s, chit_loss = %s
                WHERE id = %s;
            """, (month_index, payout_date, payout_status, full_notes, calc_amt_rec, calc_loss, membership_id))

        cur.execute("SELECT id FROM chit_schedules WHERE chit_group_id = %s AND month_index = %s;", (chit_id, month_index))
        sched_row = cur.fetchone()
        sched_id = sched_row[0] if sched_row else None

        # Member Loan Settlement Bridge
        deduct_loan_id = data.get('deduct_loan_id')
        settle_loan = bool(data.get('settle_loan', False))
        loan_settlement_info = None

        target_loan_id = deduct_loan_id
        if not target_loan_id and settle_loan:
            cur.execute("""
                SELECT id::text FROM chit_loans 
                WHERE member_id = %s AND status = 'active'
                ORDER BY disbursal_date ASC LIMIT 1;
            """, (m_id,))
            lr_found = cur.fetchone()
            if lr_found:
                target_loan_id = lr_found[0]

        if target_loan_id:
            cur.execute("""
                SELECT id, principal_amount, annual_interest_rate, disbursal_date, total_repaid_principal, total_repaid_interest
                FROM chit_loans
                WHERE id::text = %s AND member_id = %s AND status = 'active';
            """, (str(target_loan_id), m_id))
            l_data = cur.fetchone()
            if l_data:
                l_id, l_p_orig, l_rate, l_disb_date, l_rep_p, l_rep_i = l_data
                calc = calculate_loan_compound_interest(
                    principal=l_p_orig,
                    annual_rate=l_rate,
                    disbursal_date=l_disb_date,
                    as_of_date=payout_date,
                    repaid_principal=l_rep_p,
                    repaid_interest=l_rep_i
                )
                rem_payoff = calc['total_payoff']
                rem_p = calc['remaining_principal']
                rem_i = calc['accrued_interest']

                actual_deduction = min(rem_payoff, calc_amt_rec)
                if actual_deduction > 0:
                    ded_interest = min(actual_deduction, rem_i)
                    ded_principal = max(0.0, actual_deduction - ded_interest)

                    new_tot_p = float(l_rep_p or 0) + ded_principal
                    new_tot_i = float(l_rep_i or 0) + ded_interest

                    is_cleared = (rem_payoff - actual_deduction) <= 0.01
                    new_status = 'settled' if is_cleared else 'active'
                    settled_at = payout_date if is_cleared else None

                    cur.execute("""
                        UPDATE chit_loans
                        SET total_repaid_principal = %s,
                            total_repaid_interest = %s,
                            status = %s,
                            settled_at = %s,
                            settlement_type = 'chit_payout_deduction',
                            settled_from_schedule_id = %s,
                            updated_at = NOW()
                        WHERE id = %s;
                    """, (new_tot_p, new_tot_i, new_status, settled_at, sched_id, l_id))

                    repay_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO chit_loan_repayments (
                            id, loan_id, repayment_date, principal_amount, interest_amount,
                            total_amount, payment_mode, receipt_no, source_schedule_id, notes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        repay_id, l_id, payout_date, ded_principal, ded_interest,
                        actual_deduction, 'Chit Payout Deduction', f"PAYOUT-SETTLE-M{month_index}",
                        sched_id, f"Auto-settled from Chit Group '{g_name}' Month {month_index} Payout"
                    ))

                    full_notes += f" | Loan Settled: -₹{actual_deduction:,.0f} deducted (Net Disbursed: ₹{calc_amt_rec - actual_deduction:,.0f})"
                    loan_settlement_info = {
                        'loan_id': str(l_id),
                        'deducted_amount': actual_deduction,
                        'deducted_principal': ded_principal,
                        'deducted_interest': ded_interest,
                        'is_settled': is_cleared,
                        'remaining_balance': max(0.0, round_curr(rem_payoff - actual_deduction))
                    }

        # Nominal 1.0 share base values for the group schedule
        base_amt = float(m_base['amount_received'])
        base_loss = float(m_base['chit_loss'])

        cur.execute("""
            UPDATE chit_schedules
            SET lifted_by_membership_id = COALESCE(lifted_by_membership_id, %s),
                payout_date = COALESCE(payout_date, %s),
                payout_status = %s,
                amount_received = %s,
                chit_loss = %s,
                notes = COALESCE(notes, %s)
            WHERE chit_group_id = %s AND month_index = %s;
        """, (membership_id, payout_date, payout_status, base_amt, base_loss, full_notes, chit_id, month_index))

        action_name = 'PAYOUT_RECORDED' if request.method == 'POST' else 'PAYOUT_UPDATED'
        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, %s, 'CHIT_SCHEDULE', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            action_name,
            str(membership_id),
            json.dumps({'month': month_index, 'amount': calc_amt_rec, 'loss': calc_loss, 'share_count': share_count, 'status': payout_status, 'notes': full_notes, 'loan_settlement': loan_settlement_info})
        ))

        conn.commit()
        return jsonify({
            'success': True,
            'month_index': month_index,
            'payout_status': payout_status,
            'amount_received': calc_amt_rec,
            'chit_loss': calc_loss,
            'share_count': share_count,
            'lifted_shares': share_count,
            'split_created': bool(share_count < orig_shares),
            'loan_settlement': loan_settlement_info,
            'net_payout_amount': (calc_amt_rec - loan_settlement_info['deducted_amount']) if loan_settlement_info else calc_amt_rec
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

def _unlift_single_chit_membership(cur, ms_id, chit_id):
    """Helper to clean up a single lifted membership: recombine split tickets if needed, clear payout columns, and rebalance installments."""
    cur.execute("""
        SELECT member_id, ticket_number, share_units, account_number, created_at
        FROM chit_memberships WHERE id = %s;
    """, (ms_id,))
    ms_info = cur.fetchone()
    if not ms_info:
        return
    m_id, t_num, lifted_shares, acc_no, ms_created = ms_info
    lifted_shares = float(lifted_shares or 1.0)

    # Find unlifted siblings for the same member and ticket
    cur.execute("""
        SELECT id, share_units, created_at
        FROM chit_memberships 
        WHERE chit_group_id = %s AND member_id = %s AND ticket_number = %s AND has_lifted = FALSE AND id != %s
        ORDER BY created_at ASC;
    """, (chit_id, m_id, t_num, ms_id))
    sibs = cur.fetchall()

    if sibs:
        cur.execute("SELECT COUNT(*) FROM chit_payments WHERE membership_id = %s;", (ms_id,))
        ms_payments = cur.fetchone()[0]

        keeper_id = ms_id
        for s_id, s_shares, s_created in sibs:
            cur.execute("SELECT COUNT(*) FROM chit_payments WHERE membership_id = %s;", (s_id,))
            s_payments = cur.fetchone()[0]
            if s_payments > 0 and ms_payments == 0:
                keeper_id = s_id

        total_combined_shares = lifted_shares + sum(float(s[1] or 0.0) for s in sibs)
        discard_ids = [ms_id] if keeper_id != ms_id else []
        discard_ids.extend([s[0] for s in sibs if s[0] != keeper_id])

        for d_id in discard_ids:
            cur.execute("""
                UPDATE chit_payments p
                SET membership_id = %s,
                    installment_id = ki.id
                FROM chit_installments di
                JOIN chit_installments ki ON ki.membership_id = %s AND ki.month_index = di.month_index
                WHERE p.membership_id = %s AND p.installment_id = di.id;
            """, (keeper_id, keeper_id, d_id))
            cur.execute("UPDATE chit_payments SET membership_id = %s WHERE membership_id = %s;", (keeper_id, d_id))
            cur.execute("UPDATE chit_payment_requests SET membership_id = %s WHERE membership_id = %s;", (keeper_id, d_id))
            cur.execute("UPDATE chit_credit_transfers SET from_membership_id = %s WHERE from_membership_id = %s;", (keeper_id, d_id))
            cur.execute("UPDATE chit_credit_transfers SET to_membership_id = %s WHERE to_membership_id = %s;", (keeper_id, d_id))

            # Disassociate foreign keys on chit_schedules before deleting d_id
            cur.execute("UPDATE chit_schedules SET lifted_by_membership_id = NULL WHERE lifted_by_membership_id = %s;", (d_id,))
            cur.execute("UPDATE chit_schedules SET winning_membership_id = NULL WHERE winning_membership_id = %s;", (d_id,))

            cur.execute("DELETE FROM chit_installments WHERE membership_id = %s;", (d_id,))
            cur.execute("DELETE FROM chit_memberships WHERE id = %s;", (d_id,))

        cur.execute("""
            UPDATE chit_memberships
            SET share_units = %s,
                has_lifted = FALSE,
                lifted_month_index = NULL,
                payout_date = NULL,
                payout_status = NULL,
                payout_notes = NULL,
                payout_amount = NULL,
                chit_loss = NULL
            WHERE id = %s;
        """, (total_combined_shares, keeper_id))
    else:
        cur.execute("""
            UPDATE chit_memberships
            SET has_lifted = FALSE,
                lifted_month_index = NULL,
                payout_date = NULL,
                payout_status = NULL,
                payout_notes = NULL,
                payout_amount = NULL,
                chit_loss = NULL
            WHERE id = %s;
        """, (ms_id,))

    # Rebalance installments and recalculate dues for this member
    rescale_and_rebalance_member_installments(cur, m_id, chit_id)

@chit_bp.route('/api/chitgroups/<chit_id>/month/<int:month_index>/payout', methods=['DELETE'])
def delete_month_payout(chit_id, month_index):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT s.id, s.lifted_by_membership_id, g.chit_total_value, g.duration_months, 
                   g.start_month_year, g.commission_percent, g.is_month1_company_month,
                   s.payout_status, s.payout_date
            FROM chit_schedules s
            JOIN chit_groups g ON s.chit_group_id = g.id
            WHERE s.chit_group_id = %s AND s.month_index = %s;
        """, (chit_id, month_index))
        res = cur.fetchone()
        if not res:
            return jsonify({'error': 'Month schedule not found'}), 404

        sched_id, ms_id, g_val, g_dur, g_start, g_comm, g_isco, p_stat, p_date = res

        # Optional target membership_id from query params or body
        target_ms_id = request.args.get('membership_id')
        if not target_ms_id and request.is_json:
            body = request.get_json(silent=True) or {}
            target_ms_id = body.get('membership_id')

        # Query all memberships that took a payout in this month
        cur.execute("""
            SELECT id, member_id, payout_amount, share_units
            FROM chit_memberships
            WHERE chit_group_id = %s AND lifted_month_index = %s AND has_lifted = TRUE;
        """, (chit_id, month_index))
        lifted_rows = cur.fetchall()
        lifted_map = {str(r[0]): r for r in lifted_rows}

        if ms_id and str(ms_id) not in lifted_map:
            lifted_map[str(ms_id)] = (ms_id, None, None, None)

        if not lifted_map and not p_date and p_stat in (None, 'pending'):
            return jsonify({'error': 'No payout recorded for this month'}), 404

        # Determine which memberships to unlift
        if target_ms_id:
            if str(target_ms_id) not in lifted_map:
                return jsonify({'error': 'Specified subscriber payout not found in this month'}), 404
            ids_to_unlift = [str(target_ms_id)]
        else:
            ids_to_unlift = list(lifted_map.keys())

        # 1. Revert any linked loan auto-settlements for unlifted members
        for unlift_id in ids_to_unlift:
            member_row = lifted_map.get(unlift_id)
            unlift_m_id = member_row[1] if member_row else None
            if unlift_m_id:
                cur.execute("""
                    SELECT r.id, r.loan_id, r.principal_amount, r.interest_amount
                    FROM chit_loan_repayments r
                    JOIN chit_loans l ON r.loan_id = l.id
                    WHERE r.source_schedule_id = %s AND l.member_id = %s;
                """, (sched_id, unlift_m_id))
            else:
                cur.execute("""
                    SELECT id, loan_id, principal_amount, interest_amount
                    FROM chit_loan_repayments
                    WHERE source_schedule_id = %s;
                """, (sched_id,))
            loan_repays = cur.fetchall()
            for r_id, l_id, p_amt, i_amt in loan_repays:
                cur.execute("""
                    UPDATE chit_loans
                    SET total_repaid_principal = GREATEST(0, COALESCE(total_repaid_principal, 0) - %s),
                        total_repaid_interest = GREATEST(0, COALESCE(total_repaid_interest, 0) - %s),
                        status = 'active',
                        settled_at = NULL,
                        settlement_type = NULL,
                        settled_from_schedule_id = NULL,
                        updated_at = NOW()
                    WHERE id = %s;
                """, (float(p_amt or 0), float(i_amt or 0), l_id))
                cur.execute("DELETE FROM chit_loan_repayments WHERE id = %s;", (r_id,))

        # Clear foreign keys on this month's schedule referencing unlifted memberships first
        cur.execute("""
            UPDATE chit_schedules
            SET lifted_by_membership_id = NULL,
                winning_membership_id = CASE WHEN winning_membership_id::text = ANY(%s) THEN NULL ELSE winning_membership_id END
            WHERE chit_group_id = %s AND month_index = %s AND (lifted_by_membership_id::text = ANY(%s) OR winning_membership_id::text = ANY(%s));
        """, (ids_to_unlift, chit_id, month_index, ids_to_unlift, ids_to_unlift))

        # 2. Unlift each selected membership
        for unlift_id in ids_to_unlift:
            _unlift_single_chit_membership(cur, unlift_id, chit_id)

        # 3. Base schedule nominal values
        base_sched = ce.generate_chit_schedule(float(g_val), int(g_dur or 20), g_start, float(g_comm or 3.0), bool(g_isco))
        m_base = base_sched[month_index - 1]
        base_amt = float(m_base['amount_received'])
        base_loss = float(m_base['chit_loss'])

        # 4. Check if any lifted memberships remain in this month
        cur.execute("""
            SELECT id, payout_status, payout_date, payout_notes
            FROM chit_memberships
            WHERE chit_group_id = %s AND lifted_month_index = %s AND has_lifted = TRUE;
        """, (chit_id, month_index))
        remaining_lifted = cur.fetchall()

        if remaining_lifted:
            first_rem = remaining_lifted[0]
            rem_stat = 'unpaid' if any((r[1] or '').lower() == 'unpaid' for r in remaining_lifted) else 'paid'
            cur.execute("""
                UPDATE chit_schedules
                SET lifted_by_membership_id = %s,
                    winning_membership_id = CASE WHEN winning_membership_id::text = ANY(%s) THEN %s ELSE winning_membership_id END,
                    payout_date = %s,
                    payout_status = %s,
                    amount_received = %s,
                    chit_loss = %s,
                    notes = %s
                WHERE chit_group_id = %s AND month_index = %s;
            """, (first_rem[0], ids_to_unlift, first_rem[0], first_rem[2], rem_stat, base_amt, base_loss, first_rem[3], chit_id, month_index))
        else:
            cur.execute("""
                UPDATE chit_schedules
                SET lifted_by_membership_id = NULL,
                    winning_membership_id = CASE WHEN winning_membership_id::text = ANY(%s) THEN NULL ELSE winning_membership_id END,
                    payout_date = NULL,
                    payout_status = 'pending',
                    amount_received = %s,
                    chit_loss = %s,
                    notes = NULL
                WHERE chit_group_id = %s AND month_index = %s;
            """, (ids_to_unlift, base_amt, base_loss, chit_id, month_index))

        # 5. Audit Log
        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'PAYOUT_DELETED', 'CHIT_SCHEDULE', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            str(target_ms_id) if target_ms_id else str(sched_id),
            json.dumps({'month': month_index, 'deleted_memberships': ids_to_unlift, 'remaining_count': len(remaining_lifted)})
        ))

        conn.commit()
        return jsonify({
            'success': True,
            'message': f"Payout for Month {month_index} deleted successfully",
            'month_index': month_index,
            'deleted_memberships': ids_to_unlift,
            'remaining_count': len(remaining_lifted)
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@chit_bp.route('/api/chitgroups/<chit_id>/payout/<membership_id>', methods=['PUT', 'POST'])
def update_recipient_payout(chit_id, membership_id):
    """Update an individual recipient's payout details (date, payment mode/notes, status, share count) without affecting other recipients."""
    data = request.get_json() or {}
    payout_date = data.get('payout_date')
    payment_mode = (data.get('payment_mode') or 'Bank Transfer').strip()
    notes_raw = (data.get('notes') or '').strip()
    full_notes = f"{payment_mode} · {notes_raw}" if notes_raw else payment_mode
    pay_now = data.get('pay_now')
    new_status = ('paid' if pay_now else 'unpaid') if pay_now is not None else data.get('payout_status', 'paid')
    requested_shares = data.get('share_count') or data.get('share_units')

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # 1. Fetch current membership details
        cur.execute("""
            SELECT ms.chit_group_id, ms.member_id, ms.ticket_number, ms.share_units, ms.has_lifted,
                   ms.lifted_month_index, g.chit_total_value, g.duration_months, g.start_month_year,
                   g.commission_percent, g.is_month1_company_month, g.name as group_name,
                   COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                   ms.payout_date, ms.payout_status, ms.payout_notes, ms.payout_amount, ms.chit_loss
            FROM chit_memberships ms
            JOIN chit_groups g ON ms.chit_group_id = g.id
            WHERE ms.id = %s;
        """, (membership_id,))
        ms_row = cur.fetchone()
        if not ms_row:
            return jsonify({'error': 'Membership not found'}), 404

        (ms_grp_id, m_id, t_num, curr_shares, has_lift,
         lift_m_idx, g_val, g_dur, g_start, g_comm, g_isco, g_name,
         acc_no, old_date, old_stat, old_notes, old_amt, old_loss) = ms_row

        if str(ms_grp_id) != str(chit_id):
            return jsonify({'error': 'Membership does not belong to specified chit group'}), 400

        curr_shares = float(curr_shares or 1.0)
        m_idx = lift_m_idx or int(data.get('month_index') or 1)
        payout_date = payout_date or (str(old_date) if old_date else str(date.today()))

        # Base schedule for 1 nominal chit
        base_sched = ce.generate_chit_schedule(float(g_val), int(g_dur or 20), g_start, float(g_comm or 3.0), bool(g_isco))
        if m_idx < 1 or m_idx > len(base_sched):
            return jsonify({'error': 'Invalid month index'}), 400
        
        m_base = base_sched[m_idx - 1]

        # 2. Handle share count adjustments if provided
        final_shares = curr_shares
        if requested_shares is not None:
            new_shares = float(requested_shares)
            if new_shares != curr_shares:
                # Find unlifted siblings for the same member and ticket
                cur.execute("""
                    SELECT id, share_units FROM chit_memberships
                    WHERE chit_group_id = %s AND member_id = %s AND ticket_number = %s AND has_lifted = FALSE AND id != %s
                    LIMIT 1;
                """, (chit_id, m_id, t_num, membership_id))
                sib = cur.fetchone()
                sib_id = sib[0] if sib else None
                sib_shares = float(sib[1]) if sib else 0.0
                total_avail = curr_shares + sib_shares

                if 0.5 <= new_shares <= total_avail:
                    rem_shares = round_curr(total_avail - new_shares)
                    final_shares = new_shares
                    if rem_shares > 0:
                        if sib_id:
                            cur.execute("UPDATE chit_memberships SET share_units = %s WHERE id = %s;", (rem_shares, sib_id))
                        else:
                            cur.execute("""
                                INSERT INTO chit_memberships (chit_group_id, member_id, ticket_number, account_number, share_units, has_lifted)
                                VALUES (%s, %s, %s, %s, %s, FALSE);
                            """, (chit_id, m_id, t_num, acc_no, rem_shares))
                    else:
                        if sib_id:
                            cur.execute("UPDATE chit_payments SET membership_id = %s WHERE membership_id = %s;", (membership_id, sib_id))
                            cur.execute("DELETE FROM chit_installments WHERE membership_id = %s;", (sib_id,))
                            cur.execute("DELETE FROM chit_memberships WHERE id = %s;", (sib_id,))

        calc_amt_rec = round_curr(float(m_base['amount_received']) * final_shares)
        calc_loss = round_curr(float(m_base['chit_loss']) * final_shares)

        # 3. Update ONLY this membership's payout fields
        cur.execute("""
            UPDATE chit_memberships
            SET payout_date = %s,
                payout_status = %s,
                payout_notes = %s,
                payout_amount = %s,
                chit_loss = %s,
                share_units = %s,
                has_lifted = TRUE,
                lifted_month_index = %s
            WHERE id = %s;
        """, (payout_date, new_status, full_notes, calc_amt_rec, calc_loss, final_shares, m_idx, membership_id))

        # Rebalance installments if shares changed
        if final_shares != curr_shares:
            rescale_and_rebalance_member_installments(cur, m_id, chit_id)

        # 4. If this membership is the primary on chit_schedules, update schedule notes/date/status
        cur.execute("""
            SELECT lifted_by_membership_id FROM chit_schedules
            WHERE chit_group_id = %s AND month_index = %s;
        """, (chit_id, m_idx))
        sched_row = cur.fetchone()
        if sched_row and str(sched_row[0]) == str(membership_id):
            cur.execute("""
                UPDATE chit_schedules
                SET payout_date = %s,
                    payout_status = %s,
                    notes = %s
                WHERE chit_group_id = %s AND month_index = %s;
            """, (payout_date, new_status, full_notes, chit_id, m_idx))

        # 5. Audit log
        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'PAYOUT_UPDATED', 'CHIT_MEMBERSHIP', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            str(membership_id),
            json.dumps({'month': m_idx, 'payout_date': payout_date, 'amount': calc_amt_rec, 'loss': calc_loss, 'share_count': final_shares, 'status': new_status, 'notes': full_notes})
        ))

        conn.commit()
        return jsonify({
            'success': True,
            'membership_id': str(membership_id),
            'month_index': m_idx,
            'payout_date': payout_date,
            'payout_status': new_status,
            'payout_amount': calc_amt_rec,
            'chit_loss': calc_loss,
            'share_count': final_shares
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<chit_id>/month/<int:month_index>/mark-paid', methods=['POST'])
def mark_month_payout_paid(chit_id, month_index):
    data = request.get_json(silent=True) or {}
    target_ms_id = request.args.get('membership_id') or data.get('membership_id')
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, lifted_by_membership_id, amount_received
            FROM chit_schedules
            WHERE chit_group_id = %s AND month_index = %s;
        """, (chit_id, month_index))
        sched_res = cur.fetchone()
        if not sched_res:
            return jsonify({'error': 'Month schedule not found'}), 404

        sched_id, ms_id, amt = sched_res

        if target_ms_id:
            # Mark only this specific membership paid
            cur.execute("""
                UPDATE chit_memberships
                SET payout_status = 'paid'
                WHERE id = %s AND chit_group_id = %s;
            """, (target_ms_id, chit_id))

            # If all lifted memberships for this month are now paid, update chit_schedules as well
            cur.execute("""
                SELECT COUNT(*) FROM chit_memberships
                WHERE chit_group_id = %s AND lifted_month_index = %s AND has_lifted = TRUE AND payout_status != 'paid';
            """, (chit_id, month_index))
            unpaid_remaining = cur.fetchone()[0]
            if unpaid_remaining == 0:
                cur.execute("""
                    UPDATE chit_schedules SET payout_status = 'paid'
                    WHERE id = %s;
                """, (sched_id,))
        else:
            # Mark all for this month paid
            cur.execute("""
                UPDATE chit_schedules
                SET payout_status = 'paid'
                WHERE id = %s;
            """, (sched_id,))
            cur.execute("""
                UPDATE chit_memberships
                SET payout_status = 'paid'
                WHERE chit_group_id = %s AND lifted_month_index = %s AND has_lifted = TRUE;
            """, (chit_id, month_index))

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'PAYOUT_MARKED_PAID', 'CHIT_SCHEDULE', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            str(target_ms_id or ms_id or ''),
            json.dumps({'month': month_index, 'amount': float(amt or 0), 'status': 'paid', 'target_membership_id': str(target_ms_id) if target_ms_id else None})
        ))

        conn.commit()
        return jsonify({'success': True, 'message': f'Payout for Month {month_index} marked as paid / disbursed'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<chit_id>/month/<int:month_index>/record-lift', methods=['POST'])
def record_month_lift(chit_id, month_index):
    return handle_month_payout(chit_id, month_index)

@chit_bp.route('/api/payments', methods=['GET', 'POST'])
def get_payments_list():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        return process_payment_record(data)

    chit_id = request.args.get('chit_id')
    month_index = request.args.get('month_index')
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT 
                p.id, p.installment_id, p.membership_id, p.amount,
                p.payment_mode, p.payment_date, p.reference_no, p.receipt_no,
                p.receipt_url, p.notes, p.recorded_by, p.created_at,
                m.id as member_id, m.full_name as member_name, m.phone,
                ms.ticket_number, ms.share_units,
                i.month_index, i.month_year,
                g.name as chit_name, g.id as chit_id,
                COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                m.customer_id,
                COALESCE(ms.installment_type, 'incremental') as installment_type,
                COALESCE(i.net_due_amount, 0) as net_due_amount
            FROM chit_payments p
            JOIN chit_installments i ON p.installment_id = i.id
            JOIN chit_memberships ms ON p.membership_id = ms.id
            JOIN chit_members m ON ms.member_id = m.id
            JOIN chit_groups g ON i.chit_group_id = g.id
            WHERE g.deleted_at IS NULL
        """
        params = []
        if chit_id and chit_id != 'all':
            query += " AND g.id = %s"
            params.append(chit_id)
        if month_index and str(month_index).isdigit():
            query += " AND i.month_index = %s"
            params.append(int(month_index))

        query += " ORDER BY p.created_at DESC;"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        members_map = {}
        for r in rows:
            m_id = str(r[12])
            created_dt = r[11]
            time_ago_str = format_time_ago(created_dt)
            is_recent = False
            if created_dt:
                diff_sec = (datetime.now(created_dt.tzinfo) - created_dt).total_seconds()
                is_recent = diff_sec < 60

            p_amt = float(r[3])
            pay_mode = r[4] or 'Cash'
            is_credit = pay_mode.lower() in ['advance credit', 'credit settlement', 'credit adjustment']
            net_due_val = float(r[24] or 0.0) if len(r) > 24 else 0.0
            excess_c = max(0.0, round_curr(p_amt - net_due_val)) if (not is_credit and net_due_val > 0 and p_amt > net_due_val) else 0.0

            p_item = {
                'id': str(r[0]),
                'installment_id': str(r[1]),
                'membership_id': str(r[2]),
                'amount': p_amt,
                'payment_mode': pay_mode,
                'is_credit_settlement': is_credit,
                'excess_to_credit': excess_c,
                'net_due_amount': net_due_val,
                'payment_date': r[5].isoformat() if r[5] else str(date.today()),
                'reference_no': r[6] or '',
                'receipt_no': r[7] or '',
                'receipt_url': r[8] or '',
                'notes': r[9] or '',
                'recorded_by': r[10] or '',
                'created_at': created_dt.isoformat() if created_dt else None,
                'time_ago': time_ago_str,
                'is_recent': is_recent,
                'month_index': r[17],
                'month_year': r[18],
                'month_tag': f"M{r[17]} · {format_month_year(r[18])}",
                'chit_name': r[19],
                'chit_id': str(r[20]),
                'account_number': r[21],
                'customer_id': r[22] or '',
                'installment_type': r[23] or 'incremental'
            }

            if m_id not in members_map:
                members_map[m_id] = {
                    'member_id': m_id,
                    'member_name': r[13],
                    'phone': r[14] or '',
                    'ticket_number': r[15],
                    'account_number': r[21],
                    'customer_id': r[22] or '',
                    'share_units': float(r[16]),
                    'installment_type': r[23] or 'incremental',
                    'total_paid': 0.0,
                    'cash_paid': 0.0,
                    'credit_settled': 0.0,
                    'excess_to_credit': 0.0,
                    'payments_count': 0,
                    'chit_name': r[19],
                    'payments': []
                }

            members_map[m_id]['total_paid'] += p_amt
            if is_credit:
                members_map[m_id]['credit_settled'] += p_amt
            else:
                members_map[m_id]['cash_paid'] += p_amt
                members_map[m_id]['excess_to_credit'] += excess_c
            members_map[m_id]['payments_count'] += 1
            members_map[m_id]['payments'].append(p_item)

        # Query payouts recorded/disbursed for this month
        po_query = """
            SELECT 
                s.id, ms.id as membership_id, COALESCE(ms.payout_amount, (COALESCE(s.amount_received, 0) * COALESCE(ms.share_units, 1.0))),
                COALESCE(ms.payout_date, s.payout_date), COALESCE(ms.payout_status, s.payout_status),
                COALESCE(ms.payout_notes, s.notes), COALESCE(ms.created_at, s.created_at),
                m.id as member_id, m.full_name as member_name, m.phone,
                ms.ticket_number, ms.share_units,
                ms.lifted_month_index as month_index, s.month_year,
                g.name as chit_name, g.id as chit_id,
                COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                m.customer_id,
                COALESCE(ms.installment_type, 'incremental') as installment_type
            FROM chit_memberships ms
            JOIN chit_members m ON ms.member_id = m.id
            JOIN chit_groups g ON ms.chit_group_id = g.id
            LEFT JOIN chit_schedules s ON g.id = s.chit_group_id AND ms.lifted_month_index = s.month_index
            WHERE ms.has_lifted = TRUE AND ms.lifted_month_index IS NOT NULL AND g.deleted_at IS NULL
        """
        po_params = []
        if chit_id and chit_id != 'all':
            po_query += " AND g.id = %s"
            po_params.append(chit_id)
        if month_index and str(month_index).isdigit():
            po_query += " AND ms.lifted_month_index = %s"
            po_params.append(int(month_index))

        cur.execute(po_query, tuple(po_params))
        po_rows = cur.fetchall()
        payouts_list = []
        for por in po_rows:
            (s_id, ms_id, amt_rec, p_date, p_stat, p_notes, c_at,
             m_id, m_name, m_phone, t_num, s_units, m_idx, m_yr, g_name, g_id, acc_num, cust_id, inst_type) = por
            m_id = str(m_id)
            time_ago_str = format_time_ago(c_at or p_date)
            p_stat = p_stat or 'unpaid'
            mode = 'Bank Transfer'
            if p_notes and '·' in p_notes:
                mode = p_notes.split('·')[0].strip()
            elif p_notes:
                mode = p_notes

            po_item = {
                'id': f"po-{s_id}",
                'schedule_id': str(s_id),
                'is_payout': True,
                'payout_status': p_stat,
                'amount': float(amt_rec or 0.0),
                'payment_mode': mode,
                'payment_date': p_date.isoformat() if p_date else str(date.today()),
                'reference_no': '',
                'receipt_no': f"PAYOUT-M{m_idx}",
                'notes': p_notes or '',
                'created_at': c_at.isoformat() if c_at else None,
                'time_ago': time_ago_str,
                'is_recent': False,
                'month_index': m_idx,
                'month_year': m_yr,
                'month_tag': f"M{m_idx} · Payout ({'Disbursed' if p_stat == 'paid' else 'Unpaid'})",
                'chit_name': g_name,
                'chit_id': str(g_id),
                'member_id': m_id,
                'member_name': m_name,
                'phone': m_phone or '',
                'ticket_number': t_num,
                'account_number': acc_num,
                'customer_id': cust_id or '',
                'share_units': float(s_units or 1.0),
                'installment_type': inst_type or 'incremental'
            }
            payouts_list.append(po_item)

            if m_id not in members_map:
                members_map[m_id] = {
                    'member_id': m_id,
                    'member_name': m_name,
                    'phone': m_phone or '',
                    'ticket_number': t_num,
                    'account_number': acc_num,
                    'customer_id': cust_id or '',
                    'share_units': float(s_units or 1.0),
                    'installment_type': inst_type or 'incremental',
                    'total_paid': 0.0,
                    'payments_count': 0,
                    'chit_name': g_name,
                    'payments': []
                }
            members_map[m_id]['payments'].append(po_item)
            members_map[m_id]['payments_count'] += 1

        return jsonify({
            'total_members_paid': len(members_map),
            'total_payments_count': len(rows) + len(po_rows),
            'members': list(members_map.values()),
            'payouts': payouts_list
        })
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/payments/<payment_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_payment_item(payment_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        if request.method == 'GET':
            cur.execute("""
                SELECT 
                    p.id, p.installment_id, p.membership_id, p.amount,
                    p.payment_mode, p.payment_date, p.reference_no, p.receipt_no,
                    p.receipt_url, p.notes, p.created_at,
                    m.full_name, m.phone, ms.ticket_number,
                    g.id, g.name, g.chit_total_value, g.duration_months,
                    i.month_index, i.month_year, i.net_due_amount, i.paid_amount, i.pending_amount
                FROM chit_payments p
                JOIN chit_installments i ON p.installment_id = i.id
                JOIN chit_memberships ms ON p.membership_id = ms.id
                JOIN chit_members m ON ms.member_id = m.id
                JOIN chit_groups g ON i.chit_group_id = g.id
                WHERE p.id = %s;
            """, (payment_id,))
            r = cur.fetchone()
            if not r:
                return jsonify({'error': 'Payment not found'}), 404

            return jsonify({
                'id': str(r[0]),
                'installment_id': str(r[1]),
                'membership_id': str(r[2]),
                'amount': float(r[3]),
                'payment_mode': r[4] or 'Cash',
                'payment_date': r[5].isoformat() if r[5] else str(date.today()),
                'reference_no': r[6] or '',
                'receipt_no': r[7] or '',
                'receipt_url': r[8] or '',
                'notes': r[9] or '',
                'created_at': r[10].isoformat() if r[10] else None,
                'member_name': r[11],
                'phone': r[12] or '',
                'ticket_number': r[13],
                'chit_id': str(r[14]),
                'chit_name': r[15],
                'chit_total_value': float(r[16]),
                'duration_months': int(r[17]),
                'month_index': r[18],
                'month_year': r[19],
                'net_due_amount': float(r[20]),
                'paid_amount': float(r[21]),
                'pending_amount': float(r[22])
            })

        elif request.method == 'PUT':
            data = request.get_json() or {}
            new_amount = float(data.get('amount') or 0)
            payment_mode = data.get('payment_mode', 'Cash')
            payment_date_str = data.get('payment_date')
            notes = data.get('notes', '')
            reference_no = data.get('reference_no', '')
            receipt_url = data.get('receipt_url', '')

            if new_amount <= 0:
                return jsonify({'error': 'Amount must be greater than 0'}), 400

            payment_date = date.today()
            if payment_date_str:
                try:
                    payment_date = datetime.strptime(payment_date_str[:10], '%Y-%m-%d').date()
                except Exception:
                    pass

            cur.execute("SELECT amount, installment_id FROM chit_payments WHERE id = %s;", (payment_id,))
            old_row = cur.fetchone()
            if not old_row:
                return jsonify({'error': 'Payment not found'}), 404
            old_amount = float(old_row[0])
            installment_id = str(old_row[1])

            diff = new_amount - old_amount

            cur.execute("""
                UPDATE chit_payments
                SET amount = %s,
                    payment_mode = %s,
                    payment_date = %s,
                    notes = %s,
                    reference_no = %s,
                    receipt_url = %s
                WHERE id = %s;
            """, (new_amount, payment_mode, payment_date, notes, reference_no, receipt_url, payment_id))

            cur.execute("""
                UPDATE chit_installments
                SET paid_amount = GREATEST(0, paid_amount + %s),
                    pending_amount = GREATEST(0, net_due_amount - (paid_amount + %s)),
                    status = CASE 
                        WHEN (paid_amount + %s) >= net_due_amount THEN 'paid'
                        WHEN (paid_amount + %s) > 0 THEN 'partial'
                        ELSE 'due'
                    END
                WHERE id = %s
                RETURNING paid_amount, pending_amount, status;
            """, (diff, diff, diff, diff, installment_id))
            inst_res = cur.fetchone()

            # Rebalance all installments for this member to cascade credit updates
            cur.execute("""
                SELECT m.id, ms.chit_group_id 
                FROM chit_installments ci
                JOIN chit_memberships ms ON ci.membership_id = ms.id
                JOIN chit_members m ON ms.member_id = m.id
                WHERE ci.id = %s;
            """, (installment_id,))
            mem_info = cur.fetchone()
            if mem_info:
                rescale_and_rebalance_member_installments(cur, mem_info[0], mem_info[1])
                cur.execute("SELECT paid_amount, pending_amount, status FROM chit_installments WHERE id = %s;", (installment_id,))
                updated_inst = cur.fetchone()
                if updated_inst:
                    inst_res = updated_inst

            cur.execute("""
                INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
                VALUES (%s, %s, 'Updated payment entry', 'chit_payments', %s, %s);
            """, (
                get_current_actor(),
                get_current_actor_role(),
                str(payment_id),
                json.dumps({'old_amount': old_amount, 'new_amount': new_amount, 'payment_mode': payment_mode})
            ))

            conn.commit()
            return jsonify({
                'success': True,
                'payment_id': payment_id,
                'amount': new_amount,
                'paid_amount': float(inst_res[0]),
                'pending_amount': float(inst_res[1]),
                'status': inst_res[2]
            })

        elif request.method == 'DELETE':
            cur.execute("SELECT amount, installment_id FROM chit_payments WHERE id = %s;", (payment_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Payment not found'}), 404
            amount = float(row[0])
            installment_id = str(row[1])

            cur.execute("DELETE FROM chit_payments WHERE id = %s;", (payment_id,))

            cur.execute("""
                UPDATE chit_installments
                SET paid_amount = GREATEST(0, paid_amount - %s),
                    pending_amount = GREATEST(0, net_due_amount - GREATEST(0, paid_amount - %s)),
                    status = CASE 
                        WHEN GREATEST(0, paid_amount - %s) >= net_due_amount THEN 'paid'
                        WHEN GREATEST(0, paid_amount - %s) > 0 THEN 'partial'
                        ELSE 'due'
                    END
                WHERE id = %s
                RETURNING paid_amount, pending_amount, status;
            """, (amount, amount, amount, amount, installment_id))
            inst_res = cur.fetchone()

            # Rebalance all installments for this member to cascade credit reversals
            cur.execute("""
                SELECT m.id, ms.chit_group_id 
                FROM chit_installments ci
                JOIN chit_memberships ms ON ci.membership_id = ms.id
                JOIN chit_members m ON ms.member_id = m.id
                WHERE ci.id = %s;
            """, (installment_id,))
            mem_info = cur.fetchone()
            if mem_info:
                rescale_and_rebalance_member_installments(cur, mem_info[0], mem_info[1])
                cur.execute("SELECT paid_amount, pending_amount, status FROM chit_installments WHERE id = %s;", (installment_id,))
                updated_inst = cur.fetchone()
                if updated_inst:
                    inst_res = updated_inst

            cur.execute("""
                INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
                VALUES (%s, %s, 'Deleted payment entry', 'chit_payments', %s, %s);
            """, (
                get_current_actor(),
                get_current_actor_role(),
                str(payment_id),
                json.dumps({'amount_reversed': amount})
            ))

            conn.commit()
            return jsonify({
                'success': True,
                'deleted_id': payment_id,
                'paid_amount': float(inst_res[0]),
                'pending_amount': float(inst_res[1]),
                'status': inst_res[2]
            })
        return jsonify({'error': 'Method not allowed'}), 405
    finally:
        cur.close()
        conn.close()

def process_payment_record(data):
    installment_id = data.get('installment_id')
    membership_id = data.get('membership_id')
    amount = float(data.get('amount') or 0)
    payment_mode = data.get('payment_mode', 'Cash')
    payment_date_str = data.get('payment_date')
    reference_no = data.get('reference_no', '')
    receipt_url = data.get('receipt_url', '')
    notes = data.get('notes', '')

    if amount <= 0 or (not installment_id and not membership_id):
        return jsonify({'error': 'Invalid payment data'}), 400

    pay_date = date.today()
    if payment_date_str:
        try:
            pay_date = datetime.strptime(payment_date_str[:10], '%Y-%m-%d').date()
        except Exception:
            pass

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # If membership_id not supplied, look it up from installment
        if not membership_id and installment_id:
            cur.execute("SELECT membership_id FROM chit_installments WHERE id = %s;", (installment_id,))
            row = cur.fetchone()
            if row:
                membership_id = str(row[0])

        cur.execute("SELECT member_id, chit_group_id FROM chit_memberships WHERE id = %s;", (membership_id,))
        m_row = cur.fetchone()
        if not m_row:
            return jsonify({'error': 'Membership not found'}), 404
        member_id, group_id = m_row

        # Find all sibling memberships for this customer in this group
        cur.execute("SELECT id FROM chit_memberships WHERE member_id = %s AND chit_group_id = %s;", (member_id, group_id))
        sib_ms_ids = [str(r[0]) for r in cur.fetchall()]

        target_month_idx = 999999
        if installment_id:
            cur.execute("SELECT month_index FROM chit_installments WHERE id = %s;", (installment_id,))
            t_row = cur.fetchone()
            if t_row:
                target_month_idx = int(t_row[0])

        # Find all unpaid installments prior to target installment across all tickets
        cur.execute("""
            SELECT i.id, i.month_index, i.pending_amount, i.net_due_amount, i.paid_amount, s.month_year, i.membership_id
            FROM chit_installments i
            JOIN chit_schedules s ON i.chit_group_id = s.chit_group_id AND i.month_index = s.month_index
            WHERE i.membership_id::text = ANY(%s)
              AND i.month_index < %s
              AND i.pending_amount > 0
            ORDER BY i.month_index ASC, i.membership_id ASC;
        """, (sib_ms_ids, target_month_idx))
        unpaid_closed = cur.fetchall()

        alloc_queue = []
        for uc in unpaid_closed:
            alloc_queue.append({
                'id': str(uc[0]),
                'month_index': uc[1],
                'pending': float(uc[2]),
                'net': float(uc[3]),
                'paid': float(uc[4]),
                'is_arrear': True,
                'my': uc[5],
                'membership_id': str(uc[6])
            })

        # Dues for target month across all tickets for this customer
        cur.execute("""
            SELECT i.id, i.month_index, i.pending_amount, i.net_due_amount, i.paid_amount, i.month_year, i.membership_id
            FROM chit_installments i
            WHERE i.membership_id::text = ANY(%s)
              AND i.month_index = %s
              AND i.pending_amount > 0
            ORDER BY i.membership_id ASC;
        """, (sib_ms_ids, target_month_idx if target_month_idx != 999999 else 1))
        target_dues = cur.fetchall()

        for td in target_dues:
            if not any(q['id'] == str(td[0]) for q in alloc_queue):
                alloc_queue.append({
                    'id': str(td[0]),
                    'month_index': td[1],
                    'pending': float(td[2]),
                    'net': float(td[3]),
                    'paid': float(td[4]),
                    'is_arrear': False,
                    'my': td[5],
                    'membership_id': str(td[6])
                })

        rem = amount
        receipt_base = f"SDC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        payment_ids = []
        alloc_index = 1
        last_inst_id = installment_id

        for idx, inst in enumerate(alloc_queue):
            is_last = (idx == len(alloc_queue) - 1)
            alloc = rem if is_last else min(rem, inst['pending'])

            if alloc > 0:
                rcpt_no = receipt_base if len(alloc_queue) == 1 else f"{receipt_base}-{alloc_index}"
                sub_notes = notes
                if inst['is_arrear']:
                    prefix = f"Cleared M{inst['month_index']} arrear"
                    sub_notes = f"{prefix} · {notes}" if notes else prefix

                cur.execute("""
                    INSERT INTO chit_payments (
                        installment_id, membership_id, amount,
                        payment_mode, payment_date, reference_no, receipt_no,
                        receipt_url, notes, recorded_by
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s
                    ) RETURNING id;
                """, (
                    inst['id'], inst['membership_id'], alloc,
                    payment_mode, pay_date, reference_no, rcpt_no,
                    receipt_url, sub_notes, get_current_actor()
                ))
                p_id = cur.fetchone()[0]
                payment_ids.append(str(p_id))
                last_inst_id = inst['id']

                # Update installment balance
                new_paid = inst['paid'] + alloc
                new_pending = max(0.0, inst['pending'] - alloc)
                new_status = 'paid' if new_pending <= 0.01 else ('partial' if new_paid > 0 else 'due')

                cur.execute("""
                    UPDATE chit_installments
                    SET paid_amount = %s,
                        pending_amount = %s,
                        status = %s
                    WHERE id = %s;
                """, (new_paid, new_pending, new_status, inst['id']))

                rem -= alloc
                alloc_index += 1

                if rem <= 0:
                    break

        # Rebalance installments for member
        rescale_and_rebalance_member_installments(cur, member_id, group_id)

        # Sync member default status based on remaining unpaid closed installments
        cur.execute("""
            SELECT m.id, m.defaulted_manually,
                   (
                       SELECT COUNT(*) 
                       FROM chit_installments ci
                       JOIN chit_schedules cs ON ci.chit_group_id = cs.chit_group_id AND ci.month_index = cs.month_index
                       JOIN chit_memberships cms ON ci.membership_id = cms.id
                       WHERE cms.member_id = m.id
                         AND cs.status = 'Closed'
                         AND ci.pending_amount > 0
                   ) as total_missed_closed
            FROM chit_members m
            JOIN chit_memberships ms ON m.id = ms.member_id
            WHERE ms.id = %s;
        """, (membership_id,))
        m_row = cur.fetchone()
        if m_row:
            m_id, is_man, total_missed = m_row
            total_missed = int(total_missed or 0)
            if not is_man:
                if total_missed < 3:
                    cur.execute("UPDATE chit_members SET is_defaulted = FALSE, defaulted_reason = NULL, defaulted_at = NULL WHERE id = %s;", (m_id,))
                else:
                    cur.execute("UPDATE chit_members SET is_defaulted = TRUE, defaulted_reason = %s WHERE id = %s;", (f'Skipped {total_missed} repayments in closed cycles', m_id))

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'Recorded payment', 'chit_payments', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            payment_ids[0] if payment_ids else str(uuid.uuid4()),
            json.dumps({'amount': amount, 'mode': payment_mode, 'receipt_no': receipt_base, 'allocated_count': len(payment_ids)})
        ))

        conn.commit()

        # Fetch latest state of last touched installment
        cur.execute("SELECT paid_amount, pending_amount, status FROM chit_installments WHERE id = %s;", (last_inst_id,))
        final_inst = cur.fetchone() or (amount, 0, 'paid')

        return jsonify({
            'success': True,
            'payment_id': payment_ids[0] if payment_ids else None,
            'payment_ids': payment_ids,
            'receipt_no': receipt_base,
            'paid_amount': float(final_inst[0]),
            'pending_amount': float(final_inst[1]),
            'status': final_inst[2]
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/payments/quick-pay', methods=['POST'])
def record_quick_payment():
    data = request.get_json(silent=True) or {}
    return process_payment_record(data)

@chit_bp.route('/api/members/<member_id>/toggle-default', methods=['POST'])
def toggle_member_default(member_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        data = request.get_json(silent=True) or {}
        is_def = bool(data.get('is_defaulted', False))
        reason = data.get('reason') or ('Marked manually by admin' if is_def else '')

        cur.execute("""
            UPDATE chit_members
            SET is_defaulted = %s,
                defaulted_manually = %s,
                defaulted_reason = %s,
                defaulted_at = CASE WHEN %s THEN NOW() ELSE NULL END
            WHERE id = %s
            RETURNING id, full_name, is_defaulted, defaulted_reason;
        """, (is_def, True, reason, is_def, member_id))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Member not found'}), 404

        conn.commit()
        return jsonify({
            'success': True,
            'member_id': str(row[0]),
            'full_name': row[1],
            'is_defaulted': row[2],
            'defaulted_reason': row[3]
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/members/link', methods=['POST'])
def link_members():
    data = request.get_json(silent=True) or {}
    member_ids = data.get('member_ids') or []
    if not isinstance(member_ids, list) or len(member_ids) < 2:
        return jsonify({'error': 'Please select at least 2 members to link'}), 400
    
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        # Check existing linked_group_ids for these members
        cur.execute("SELECT linked_group_id FROM chit_members WHERE id::text = ANY(%s) AND linked_group_id IS NOT NULL;", (member_ids,))
        existing_groups = list({str(r[0]) for r in cur.fetchall() if r[0]})
        
        target_group_id = existing_groups[0] if existing_groups else str(uuid.uuid4())
        
        # Merge if multiple existing group IDs
        if len(existing_groups) > 1:
            cur.execute("UPDATE chit_members SET linked_group_id = %s WHERE linked_group_id::text = ANY(%s);", (target_group_id, existing_groups))
            
        cur.execute("UPDATE chit_members SET linked_group_id = %s WHERE id::text = ANY(%s);", (target_group_id, member_ids))
        conn.commit()
        return jsonify({
            'success': True,
            'linked_group_id': str(target_group_id),
            'linked_count': len(member_ids)
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/members/<member_id>/unlink', methods=['POST'])
def unlink_member(member_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT linked_group_id FROM chit_members WHERE id = %s;", (member_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            return jsonify({'success': True, 'message': 'Member is not linked'})
        
        gid = row[0]
        cur.execute("UPDATE chit_members SET linked_group_id = NULL WHERE id = %s;", (member_id,))
        
        # Check how many members remain in this group
        cur.execute("SELECT count(*) FROM chit_members WHERE linked_group_id = %s;", (gid,))
        rem = cur.fetchone()[0]
        if rem <= 1:
            cur.execute("UPDATE chit_members SET linked_group_id = NULL WHERE linked_group_id = %s;", (gid,))
        
        conn.commit()
        return jsonify({'success': True, 'remaining_count': rem})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/members/<member_id>/linked-accounts', methods=['GET'])
def get_member_linked_accounts(member_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, full_name, customer_id, phone, linked_group_id FROM chit_members WHERE id = %s;", (member_id,))
        m = cur.fetchone()
        if not m:
            return jsonify({'error': 'Member not found'}), 404
        
        linked_members = []
        gid = m[4]
        if gid:
            cur.execute("""
                SELECT 
                    m.id::text, 
                    m.full_name, 
                    COALESCE(m.customer_id, '') as customer_id,
                    m.phone,
                    COALESCE((
                        SELECT COALESCE(ms.account_number, ms.ticket_number::text)
                        FROM chit_memberships ms
                        JOIN chit_groups g ON ms.chit_group_id = g.id
                        WHERE ms.member_id = m.id AND g.deleted_at IS NULL
                        ORDER BY ms.created_at ASC
                        LIMIT 1
                    ), '') as primary_account_number,
                    COALESCE((
                        SELECT COUNT(DISTINCT ms.chit_group_id)
                        FROM chit_memberships ms
                        JOIN chit_groups g ON ms.chit_group_id = g.id
                        WHERE ms.member_id = m.id AND g.deleted_at IS NULL
                    ), 0) as active_chits_count
                FROM chit_members m
                WHERE m.linked_group_id = %s
                ORDER BY m.customer_id ASC, m.full_name ASC;
            """, (gid,))
            for lm in cur.fetchall():
                linked_members.append({
                    'id': lm[0],
                    'full_name': lm[1],
                    'customer_id': lm[2],
                    'phone': lm[3] or '',
                    'account_number': lm[4] or '',
                    'active_chits_count': int(lm[5]),
                    'is_current': lm[0] == str(member_id)
                })
        
        # All other members for candidate linking search
        cur.execute("""
            SELECT 
                m.id::text,
                m.full_name,
                COALESCE(m.customer_id, '') as customer_id,
                m.phone,
                COALESCE((
                    SELECT COALESCE(ms.account_number, ms.ticket_number::text)
                    FROM chit_memberships ms
                    JOIN chit_groups g ON ms.chit_group_id = g.id
                    WHERE ms.member_id = m.id AND g.deleted_at IS NULL
                    ORDER BY ms.created_at ASC
                    LIMIT 1
                ), '') as primary_account_number,
                (m.linked_group_id IS NOT NULL AND m.linked_group_id = %s) as is_linked
            FROM chit_members m
            WHERE m.id != %s AND (m.linked_group_id IS NULL OR %s IS NULL OR m.linked_group_id != %s)
            ORDER BY m.customer_id ASC, m.full_name ASC;
        """, (gid, member_id, gid, gid))
        candidates = []
        for c in cur.fetchall():
            candidates.append({
                'id': c[0],
                'full_name': c[1],
                'customer_id': c[2],
                'phone': c[3] or '',
                'account_number': c[4] or '',
                'is_linked': bool(c[5])
            })
            
        return jsonify({
            'member_id': str(m[0]),
            'full_name': m[1],
            'linked_group_id': str(gid) if gid else None,
            'linked_members': linked_members,
            'candidates': candidates
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/dashboard/trend', methods=['GET'])
def get_dashboard_trend():
    chit_id = request.args.get('chit_id')
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT g.id, g.name, g.chit_total_value, g.current_month_index,
                   COALESCE((
                       SELECT SUM(i.net_due_amount)
                       FROM chit_installments i
                       WHERE i.chit_group_id = g.id AND i.month_index = g.current_month_index
                   ), 0) as target_month,
                   COALESCE((
                       SELECT SUM(p.amount)
                       FROM chit_payments p
                       JOIN chit_installments i ON p.installment_id = i.id
                       WHERE i.chit_group_id = g.id AND i.month_index = g.current_month_index
                         AND LOWER(COALESCE(p.payment_mode, 'cash')) NOT IN ('advance credit', 'credit settlement', 'credit adjustment')
                   ), 0) as collected_month,
                   COALESCE((
                       SELECT SUM(i.pending_amount)
                       FROM chit_installments i
                       WHERE i.chit_group_id = g.id AND i.month_index = g.current_month_index
                   ), 0) as pending_month
            FROM chit_groups g
            WHERE g.deleted_at IS NULL AND g.status = 'Active'
            ORDER BY g.created_at ASC;
        """)
        group_rows = cur.fetchall()
        per_chit = []
        for gr in group_rows:
            target = float(gr[4])
            collected = float(gr[5])
            pending = float(gr[6])
            pct = round((collected / target * 100) if target > 0 else 0)
            per_chit.append({
                'id': str(gr[0]),
                'name': gr[1],
                'target': target,
                'collected': collected,
                'pending': pending,
                'percent': pct
            })

        months_labels = ["APR '26", "MAY '26", "JUN '26", "JUL '26", "AUG '26", "SEP '26"]
        collected_points = [0, 0, 0, 0, 0, 0]
        pending_points = [0, 0, 0, 0, 0, 0]

        tot_target = sum(pc['target'] for pc in per_chit)
        tot_collected = sum(pc['collected'] for pc in per_chit)
        tot_pending = sum(pc['pending'] for pc in per_chit)

        collected_points[-1] = tot_collected
        pending_points[-1] = tot_pending

        return jsonify({
            'per_chit': per_chit,
            'months': months_labels,
            'collected_points': collected_points,
            'pending_points': pending_points,
            'total_target': tot_target,
            'total_collected': tot_collected,
            'total_pending': tot_pending
        })
    finally:
        cur.close()
        conn.close()


@chit_bp.route('/api/payments/settle-credit', methods=['POST'])
def settle_payment_with_credit():
    data = request.get_json(silent=True) or {}
    installment_id = data.get('installment_id')
    membership_id = data.get('membership_id')
    custom_amount = data.get('amount')
    notes = data.get('notes', '')

    if not installment_id and not membership_id:
        return jsonify({'error': 'Installment or membership ID is required'}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        if not membership_id and installment_id:
            cur.execute("SELECT membership_id FROM chit_installments WHERE id = %s;", (installment_id,))
            row = cur.fetchone()
            if row:
                membership_id = str(row[0])

        cur.execute("""
            SELECT ms.member_id, ms.chit_group_id, i.id, i.month_index, i.net_due_amount, i.paid_amount, i.pending_amount, i.status
            FROM chit_memberships ms
            JOIN chit_installments i ON i.membership_id = ms.id
            WHERE i.id = %s;
        """, (installment_id,))
        inst_row = cur.fetchone()
        if not inst_row:
            return jsonify({'error': 'Installment not found'}), 404

        member_id, group_id, inst_id, m_idx, net_due, cur_paid, cur_pending, cur_status = inst_row
        net_due = float(net_due or 0.0)
        cur_paid = float(cur_paid or 0.0)
        cur_pending = float(cur_pending or 0.0)

        effective_pending = cur_pending if cur_pending > 0 else max(0.0, net_due - cur_paid)
        if effective_pending <= 0.01:
            return jsonify({'error': 'This installment is already fully paid.'}), 400

        # Calculate available advance credit for this member in this group
        avail_credit = get_member_group_available_credit(cur, member_id, group_id)

        if avail_credit <= 0.01:
            return jsonify({'error': 'No available advance credit found for this member in this chit group.'}), 400

        settle_amt = min(effective_pending, avail_credit)
        if custom_amount is not None:
            try:
                c_amt = float(custom_amount)
                if 0 < c_amt <= avail_credit:
                    settle_amt = min(c_amt, effective_pending)
            except (ValueError, TypeError):
                pass

        if settle_amt <= 0.01:
            return jsonify({'error': 'Settlement amount must be greater than 0.'}), 400

        receipt_no = f"CR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        cur.execute("""
            INSERT INTO chit_payments (
                installment_id, membership_id, amount,
                payment_mode, payment_date, reference_no, receipt_no,
                notes, recorded_by
            ) VALUES (
                %s, %s, %s,
                'Advance Credit', CURRENT_DATE, %s, %s,
                %s, %s
            ) RETURNING id;
        """, (
            inst_id, membership_id, settle_amt,
            f"CREDIT-M{m_idx}", receipt_no,
            notes or f"Settled from available advance credit for Month {m_idx}",
            get_current_actor()
        ))
        p_id = cur.fetchone()[0]

        new_paid = round_curr(cur_paid + settle_amt)
        new_pending = max(0.0, round_curr(net_due - new_paid))
        new_status = 'paid' if new_pending <= 0.01 else 'partial'

        cur.execute("""
            UPDATE chit_installments
            SET paid_amount = %s,
                pending_amount = %s,
                status = %s
            WHERE id = %s;
        """, (new_paid, new_pending, new_status, inst_id))

        rescale_and_rebalance_member_installments(cur, member_id, group_id)

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'Settled installment with credit', 'chit_payments', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            str(p_id),
            json.dumps({'amount': settle_amt, 'receipt_no': receipt_no, 'month_index': m_idx})
        ))

        conn.commit()

        new_avail = get_member_group_available_credit(cur, member_id, group_id)

        return jsonify({
            'success': True,
            'payment_id': str(p_id),
            'receipt_no': receipt_no,
            'settled_amount': settle_amt,
            'paid_amount': new_paid,
            'pending_amount': new_pending,
            'status': new_status,
            'remaining_credit': new_avail
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@chit_bp.route('/api/members/<member_id>/transfer-credit', methods=['POST'])
def transfer_member_credit(member_id):
    data = request.get_json(silent=True) or {}
    from_group_id = data.get('from_group_id')
    to_group_id = data.get('to_group_id')
    amount = float(data.get('amount') or 0.0)
    notes = data.get('notes', '')

    if not from_group_id or not to_group_id:
        return jsonify({'error': 'Source and destination chit groups are required'}), 400
    if from_group_id == to_group_id:
        return jsonify({'error': 'Source and destination chit groups must be different'}), 400
    if amount <= 0.01:
        return jsonify({'error': 'Transfer amount must be greater than 0'}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM chit_memberships WHERE member_id = %s AND chit_group_id = %s;", (member_id, from_group_id))
        from_ms = cur.fetchone()
        if not from_ms:
            return jsonify({'error': 'Member is not enrolled in the source chit group'}), 400
        from_ms_id = str(from_ms[0])

        cur.execute("SELECT id FROM chit_memberships WHERE member_id = %s AND chit_group_id = %s;", (member_id, to_group_id))
        to_ms = cur.fetchone()
        if not to_ms:
            return jsonify({'error': 'Member is not enrolled in the destination chit group'}), 400
        to_ms_id = str(to_ms[0])

        avail = get_member_group_available_credit(cur, member_id, from_group_id)
        if amount > avail + 0.01:
            return jsonify({'error': f"Insufficient advance credit in source chit group (Available: ₹{int(avail):,})"}), 400

        cur.execute("""
            INSERT INTO chit_credit_transfers (
                member_id, from_group_id, from_membership_id,
                to_group_id, to_membership_id, amount, notes, transferred_by
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s, %s
            ) RETURNING id;
        """, (
            member_id, from_group_id, from_ms_id,
            to_group_id, to_ms_id, amount, notes, get_current_actor()
        ))
        transfer_id = str(cur.fetchone()[0])

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'Transferred advance credit across chits', 'chit_credit_transfers', %s, %s);
        """, (
            get_current_actor(),
            get_current_actor_role(),
            transfer_id,
            json.dumps({
                'member_id': str(member_id),
                'from_group_id': str(from_group_id),
                'to_group_id': str(to_group_id),
                'amount': amount,
                'notes': notes
            })
        ))

        conn.commit()

        new_from_avail = get_member_group_available_credit(cur, member_id, from_group_id)
        new_to_avail = get_member_group_available_credit(cur, member_id, to_group_id)
        wallet = get_member_credit_wallet(cur, member_id)

        return jsonify({
            'success': True,
            'transfer_id': transfer_id,
            'transferred_amount': amount,
            'source_remaining_credit': new_from_avail,
            'destination_credit': new_to_avail,
            'credit_wallet': wallet
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@chit_bp.route('/api/payments/mark-all-paid', methods=['POST'])
def mark_all_paid():
    data = request.get_json() or {}
    chit_id = data.get('chit_id')
    month_index = int(data.get('month_index') or 1)
    payment_mode = data.get('payment_mode', 'Cash')

    if not chit_id:
        return jsonify({'error': 'Chit group required'}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        if chit_id == 'all':
            cur.execute("""
                SELECT i.id, i.membership_id, i.pending_amount
                FROM chit_installments i
                JOIN chit_groups g ON i.chit_group_id = g.id
                WHERE g.deleted_at IS NULL AND i.month_index = %s AND i.pending_amount > 0;
            """, (month_index,))
        else:
            cur.execute("""
                SELECT id, membership_id, pending_amount
                FROM chit_installments
                WHERE chit_group_id = %s AND month_index = %s AND pending_amount > 0;
            """, (chit_id, month_index))
        pending_rows = cur.fetchall()

        count = 0
        total_recorded = 0.0

        for r in pending_rows:
            inst_id = r[0]
            ms_id = r[1]
            pend = float(r[2])

            receipt_no = f"SDC-BULK-{datetime.now().strftime('%Y%m%d%H%M%S')}-{count+1}"
            cur.execute("""
                INSERT INTO chit_payments (
                    installment_id, membership_id, amount,
                    payment_mode, payment_date, receipt_no, notes, recorded_by
                ) VALUES (
                    %s, %s, %s,
                    %s, CURRENT_DATE, %s, 'Mark all paid', %s
                );
            """, (inst_id, ms_id, pend, payment_mode, receipt_no, get_current_actor()))

            cur.execute("""
                UPDATE chit_installments
                SET paid_amount = net_due_amount,
                    pending_amount = 0.00,
                    status = 'paid'
                WHERE id = %s;
            """, (inst_id,))

            count += 1
            total_recorded += pend

        conn.commit()
        return jsonify({
            'success': True,
            'recorded_count': count,
            'total_amount': total_recorded
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/chitgroups/<chit_id>/close-month', methods=['POST'])
def close_month(chit_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        req_data = request.get_json(silent=True) or {}
        req_month = req_data.get('month_index')

        target_ids = []
        if chit_id == 'all':
            cur.execute("SELECT id FROM chit_groups WHERE status = 'Active';")
            target_ids = [str(r[0]) for r in cur.fetchall()]
        else:
            target_ids = [chit_id]

        if not target_ids:
            return jsonify({'error': 'No chit groups found'}), 404

        prev_month = 1
        new_curr_month = 2

        for gid in target_ids:
            cur.execute("SELECT current_month_index, duration_months FROM chit_groups WHERE id = %s;", (gid,))
            grow = cur.fetchone()
            if not grow:
                continue

            cur_m, duration = grow
            target_close_m = int(req_month) if req_month else cur_m

            # Close target month schedule
            cur.execute("UPDATE chit_schedules SET status = 'Closed' WHERE chit_group_id = %s AND month_index = %s;", (gid, target_close_m))

            next_m = max(cur_m, target_close_m) + 1
            if next_m <= duration:
                cur.execute("UPDATE chit_groups SET current_month_index = %s WHERE id = %s;", (next_m, gid))
                ensure_group_month_installments(cur, gid, next_m)

            prev_month = target_close_m
            new_curr_month = min(next_m, duration)

        conn.commit()
        return jsonify({
            'success': True,
            'previous_month': prev_month,
            'new_current_month': new_curr_month
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# -------------------------------------------------------------
# MEMBERS & AUDIT ENDPOINTS
# -------------------------------------------------------------

@chit_bp.route('/api/members/next-id', methods=['GET'])
def get_next_customer_id():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(MAX(customer_id::integer), 10000) + 1 FROM chit_members WHERE customer_id ~ '^[0-9]{5}$';")
        val = cur.fetchone()[0] or 10001
        return jsonify({'next_id': f"{val:05d}"})
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/members', methods=['GET', 'POST'])
def handle_members():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        if request.method == 'GET':
            cur.execute("""
                SELECT 
                    m.id, 
                    COALESCE(m.customer_id, '') as customer_id,
                    m.full_name, 
                    m.phone, 
                    m.email, 
                    m.member_portal_enabled,
                    COALESCE((
                        SELECT COUNT(DISTINCT ms.chit_group_id) 
                        FROM chit_memberships ms 
                        JOIN chit_groups g ON ms.chit_group_id = g.id 
                        WHERE ms.member_id = m.id AND g.deleted_at IS NULL
                    ), 0) as groups_count,
                    COALESCE((
                        SELECT SUM(ms.share_units) 
                        FROM chit_memberships ms 
                        JOIN chit_groups g ON ms.chit_group_id = g.id 
                        WHERE ms.member_id = m.id AND g.deleted_at IS NULL
                    ), 0) as total_shares,
                    COALESCE((
                        SELECT SUM(ms.share_units) 
                        FROM chit_memberships ms 
                        JOIN chit_groups g ON ms.chit_group_id = g.id 
                        WHERE ms.member_id = m.id AND ms.has_lifted = TRUE AND g.deleted_at IS NULL
                    ), 0) as payout_shares,
                    COALESCE((
                        SELECT SUM(i.pending_amount) 
                        FROM chit_installments i 
                        JOIN chit_memberships ms ON i.membership_id = ms.id 
                        JOIN chit_groups g ON ms.chit_group_id = g.id
                        WHERE ms.member_id = m.id AND g.deleted_at IS NULL AND i.month_index <= g.current_month_index
                    ), 0) as total_dues,
                    COALESCE(m.is_defaulted, FALSE) as is_defaulted,
                    COALESCE(m.defaulted_reason, '') as defaulted_reason,
                    m.linked_group_id::text as linked_group_id,
                    COALESCE((
                        SELECT COUNT(*) 
                        FROM chit_members lm 
                        WHERE lm.linked_group_id = m.linked_group_id AND lm.linked_group_id IS NOT NULL
                    ), 0) as linked_count
                FROM chit_members m
                ORDER BY m.customer_id ASC, m.full_name ASC;
            """)
            rows = cur.fetchall()
            members = []
            for r in rows:
                members.append({
                    'id': str(r[0]),
                    'customer_id': r[1],
                    'name': r[2],
                    'phone': r[3] or '—',
                    'email': r[4] or '—',
                    'portal_enabled': bool(r[5]),
                    'groups_count': int(r[6]),
                    'total_shares': float(r[7]),
                    'payout_shares': float(r[8]),
                    'active_chits_count': int(r[6]),
                    'total_dues': float(r[9]),
                    'is_defaulted': bool(r[10]),
                    'defaulted_reason': r[11] or '',
                    'linked_group_id': r[12],
                    'linked_count': int(r[13])
                })
            return jsonify(members)
        
        data = request.get_json() or {}
        name = (data.get('full_name') or '').strip()
        phone = (data.get('phone') or '').strip()
        email = (data.get('email') or '').strip()
        address = (data.get('address') or '').strip()
        govt_id_type = (data.get('govt_id_type') or 'Aadhaar').strip()
        govt_id_number = (data.get('govt_id_number') or data.get('aadhaar_no') or '').strip()
        govt_id_last4 = (data.get('govt_id_last4') or '').strip()
        if govt_id_number and not govt_id_last4:
            govt_id_last4 = govt_id_number[-4:] if len(govt_id_number) >= 4 else govt_id_number
        portal_enabled = bool(data.get('member_portal_enabled', data.get('portal_enabled', True)))
        nominee_name = (data.get('nominee_name') or '').strip()
        nominee_phone = (data.get('nominee_phone') or '').strip()
        nominee_relation = (data.get('nominee_relation') or '').strip()
        cust_id = (data.get('customer_id') or '').strip()

        if not name:
            return jsonify({'error': 'Member name is required'}), 400

        # Customer ID: must be 5 digits and unique
        if cust_id:
            if not (len(cust_id) == 5 and cust_id.isdigit()):
                return jsonify({'error': 'Customer ID must be exactly 5 digits (e.g. 10001)'}), 400
            cur.execute("SELECT id FROM chit_members WHERE customer_id = %s;", (cust_id,))
            if cur.fetchone():
                return jsonify({'error': f"Customer ID '{cust_id}' is already assigned to another subscriber."}), 400
        else:
            cur.execute("SELECT COALESCE(MAX(customer_id::integer), 10000) + 1 FROM chit_members WHERE customer_id ~ '^[0-9]{5}$';")
            next_id = cur.fetchone()[0] or 10001
            cust_id = f"{next_id:05d}"
            while True:
                cur.execute("SELECT id FROM chit_members WHERE customer_id = %s;", (cust_id,))
                if not cur.fetchone():
                    break
                next_id += 1
                cust_id = f"{next_id:05d}"

        cur.execute("""
            INSERT INTO chit_members (
                customer_id, full_name, phone, email, address,
                govt_id_type, govt_id_number, govt_id_last4,
                member_portal_enabled, nominee_name, nominee_phone, nominee_relation
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            cust_id, name, phone, email, address,
            govt_id_type, govt_id_number, govt_id_last4,
            portal_enabled, nominee_name, nominee_phone, nominee_relation
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({'success': True, 'id': str(new_id), 'customer_id': cust_id, 'name': name})
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/members/<member_id>/summary', methods=['GET'])
def get_member_summary(member_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, full_name, phone, govt_id_last4, COALESCE(customer_id, '') FROM chit_members WHERE id = %s;", (member_id,))
        mrow = cur.fetchone()
        if not mrow:
            return jsonify({'error': 'Member not found'}), 404

        cur.execute("""
            SELECT ms.id, ms.chit_group_id, ms.ticket_number, ms.share_units, ms.has_lifted, ms.lifted_month_index,
                   g.name, g.chit_total_value, g.duration_months, g.current_month_index,
                   COALESCE(ms.account_number, ms.ticket_number::text) as account_number
            FROM chit_memberships ms
            JOIN chit_groups g ON ms.chit_group_id = g.id
            WHERE ms.member_id = %s;
        """, (member_id,))
        chits = cur.fetchall()

        results = []
        for c in chits:
            ms_id, g_id, t_num, share, has_lift, lift_m, g_name, g_val, duration, cur_m, acc_no = c
            
            cur.execute("""
                SELECT month_index, chit_loss, amount_received, bonus, installment_kattubadi
                FROM chit_schedules
                WHERE chit_group_id = %s
                ORDER BY month_index ASC;
            """, (g_id,))
            sched_rows = cur.fetchall()
            sched = [{
                'month_index': r[0],
                'chit_loss': float(r[1]),
                'amount_received': float(r[2]),
                'bonus': float(r[3]),
                'installment_kattubadi': float(r[4])
            } for r in sched_rows]

            fin = ce.calculate_member_financials(sched, lift_m if has_lift else None, cur_m, float(share))
            results.append({
                'membership_id': str(ms_id),
                'chit_group_id': str(g_id),
                'group_name': g_name,
                'ticket_number': t_num,
                'account_number': acc_no,
                'has_lifted': has_lift,
                'lifted_month_index': lift_m,
                'financials': fin
            })

        return jsonify({
            'member_id': str(mrow[0]),
            'customer_id': mrow[4],
            'full_name': mrow[1],
            'phone': mrow[2],
            'enrollments': results
        })
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/members/<member_id>/folio', methods=['GET'])
def get_member_folio(member_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, full_name, phone, email, address, govt_id_type, govt_id_last4,
                   member_portal_enabled, nominee_name, nominee_phone, nominee_relation, created_at,
                   COALESCE(customer_id, ''),
                   COALESCE(is_defaulted, FALSE),
                   COALESCE(defaulted_manually, FALSE),
                   COALESCE(defaulted_reason, ''),
                   defaulted_at,
                   linked_group_id
            FROM chit_members
            WHERE id = %s;
        """, (member_id,))
        mrow = cur.fetchone()
        if not mrow:
            return jsonify({'error': 'Member not found'}), 404

        # Linked members if any
        linked_members = []
        if mrow[17]:
            cur.execute("""
                SELECT 
                    m.id::text, 
                    m.full_name, 
                    COALESCE(m.customer_id, '') as customer_id,
                    m.phone,
                    COALESCE((
                        SELECT COALESCE(ms.account_number, ms.ticket_number::text)
                        FROM chit_memberships ms
                        JOIN chit_groups g ON ms.chit_group_id = g.id
                        WHERE ms.member_id = m.id AND g.deleted_at IS NULL
                        ORDER BY ms.created_at ASC
                        LIMIT 1
                    ), '') as primary_account_number,
                    COALESCE((
                        SELECT COUNT(DISTINCT ms.chit_group_id)
                        FROM chit_memberships ms
                        JOIN chit_groups g ON ms.chit_group_id = g.id
                        WHERE ms.member_id = m.id AND g.deleted_at IS NULL
                    ), 0) as active_chits_count,
                    COALESCE((
                        SELECT SUM(i.pending_amount)
                        FROM chit_installments i
                        JOIN chit_memberships ms ON i.membership_id = ms.id
                        JOIN chit_groups g ON ms.chit_group_id = g.id
                        WHERE ms.member_id = m.id AND g.deleted_at IS NULL AND i.month_index <= g.current_month_index
                    ), 0) as total_dues
                FROM chit_members m
                WHERE m.linked_group_id = %s
                ORDER BY m.customer_id ASC, m.full_name ASC;
            """, (mrow[17],))
            for lm in cur.fetchall():
                linked_members.append({
                    'id': lm[0],
                    'full_name': lm[1],
                    'customer_id': lm[2],
                    'phone': lm[3] or '',
                    'account_number': lm[4] or '',
                    'active_chits_count': int(lm[5]),
                    'total_dues': float(lm[6]),
                    'is_current': lm[0] == str(member_id)
                })

        # Memberships
        cur.execute("""
            SELECT ms.id, ms.chit_group_id, ms.ticket_number, ms.share_units, ms.has_lifted, ms.lifted_month_index,
                   g.name, g.chit_total_value, g.duration_months, g.current_month_index, g.start_month_year,
                   COALESCE(ms.account_number, ms.ticket_number::text) as account_number,
                   COALESCE(ms.installment_type, 'incremental') as installment_type
            FROM chit_memberships ms
            JOIN chit_groups g ON ms.chit_group_id = g.id
            WHERE ms.member_id = %s
            ORDER BY ms.created_at ASC;
        """, (member_id,))
        m_rows = cur.fetchall()

        ms_ids = [str(mr[0]) for mr in m_rows]
        group_ids = list({str(mr[1]) for mr in m_rows})

        # Batch-fetch payments for member
        payments = []
        actual_paid_by_inst = defaultdict(float)
        actual_cash_by_inst = defaultdict(float)
        actual_credit_by_inst = defaultdict(float)
        cur.execute("""
            SELECT p.id, p.installment_id, p.membership_id, p.amount, p.payment_mode, p.payment_date,
                   p.receipt_no, p.notes, p.created_at, g.name as group_name, g.id as group_id,
                   i.month_index, i.month_year, COALESCE(i.net_due_amount, 0)
            FROM chit_payments p
            JOIN chit_memberships ms ON p.membership_id = ms.id
            JOIN chit_groups g ON ms.chit_group_id = g.id
            LEFT JOIN chit_installments i ON p.installment_id = i.id
            WHERE ms.member_id = %s
            ORDER BY p.payment_date DESC, p.created_at DESC;
        """, (member_id,))
        for pr in cur.fetchall():
            p_id, ins_id, ms_id_val, amt, mode, p_date, rec_no, notes, c_at, grp_name, grp_id, m_idx, m_yr, n_due = pr
            d_obj = p_date if isinstance(p_date, (datetime, date)) else None
            d_target = d_obj or c_at
            d_month = d_target.strftime("%b").upper() if d_target else "NOV"
            d_day = d_target.strftime("%d") if d_target else "16"
            is_credit = (mode or '').strip().lower() in ('advance credit', 'credit settlement', 'credit adjustment')
            amt_val = float(amt or 0.0)
            n_due_val = float(n_due or 0.0)
            excess_c = max(0.0, round_curr(amt_val - n_due_val)) if (not is_credit and n_due_val > 0 and amt_val > n_due_val) else 0.0

            if ins_id:
                actual_paid_by_inst[str(ins_id)] += amt_val
                if is_credit:
                    actual_credit_by_inst[str(ins_id)] += amt_val
                else:
                    actual_cash_by_inst[str(ins_id)] += amt_val

            payments.append({
                'id': str(p_id),
                'installment_id': str(ins_id) if ins_id else None,
                'membership_id': str(ms_id_val),
                'amount': amt_val,
                'payment_mode': mode or 'Cash',
                'is_credit_settlement': is_credit,
                'excess_to_credit': excess_c,
                'net_due_amount': n_due_val,
                'payment_date': p_date.isoformat() if p_date else None,
                'receipt_no': rec_no or '—',
                'notes': notes or '',
                'group_name': grp_name,
                'group_id': str(grp_id),
                'month_index': m_idx,
                'month_year': m_yr,
                'month_tag': f"Month {m_idx}" if m_idx else 'Installment',
                'date_month': d_month,
                'date_day': d_day,
                'time_ago': format_time_ago(d_target),
                'created_at': c_at.isoformat() if c_at else None
            })

        # Calculate exact credit wallet using unified credit engine
        credit_wallet = get_member_credit_wallet(cur, member_id)
        credits_by_grp = {pg['group_id']: pg['available_credit'] for pg in credit_wallet.get('per_group', [])}
        credits_by_ms = defaultdict(float)
        for mr in m_rows:
            credits_by_ms[str(mr[0])] = credits_by_grp.get(str(mr[1]), 0.0)

        # Batch-fetch installments for all memberships (eliminates N+1 query)
        inst_map_by_ms = defaultdict(dict)
        if ms_ids:
            cur.execute("""
                SELECT membership_id::text, id, month_index, month_year, net_due_amount, paid_amount, pending_amount, status
                FROM chit_installments
                WHERE membership_id::text = ANY(%s)
                ORDER BY month_index ASC;
            """, (ms_ids,))
            for r in cur.fetchall():
                inst_map_by_ms[str(r[0])][r[2]] = r[1:]

        # Batch-fetch schedules for all chit groups (eliminates N+1 query)
        sched_rows_by_group = defaultdict(list)
        sched_map_by_group = defaultdict(dict)
        if group_ids:
            cur.execute("""
                SELECT chit_group_id::text, month_index, chit_loss, amount_received, bonus, installment_kattubadi, status, month_year
                FROM chit_schedules
                WHERE chit_group_id::text = ANY(%s)
                ORDER BY month_index ASC;
            """, (group_ids,))
            for sr in cur.fetchall():
                grp_id = str(sr[0])
                row_data = sr[1:]
                sched_rows_by_group[grp_id].append(row_data)
                sched_map_by_group[grp_id][row_data[0]] = row_data

        chits = []
        payouts_list = []
        total_paid_in = 0.0
        total_credit_settled = 0.0
        total_paid_out = 0.0
        total_pending_dues = 0.0
        total_months_count = 0
        months_paid_count = 0
        all_unpaid_items = []
        due_now_item = None

        for mr in m_rows:
            ms_id, g_id, t_num, share, has_lift, lift_m, g_name, g_val, duration, cur_m, start_my, acc_no, inst_type = mr
            share = float(share or 1.0)
            g_val = float(g_val or 0.0)
            duration = int(duration or 20)
            cur_m = int(cur_m or 1)
            total_months_count += duration

            # Installments (pre-fetched in batch)
            inst_map = inst_map_by_ms.get(str(ms_id), {})

            group_paid_months = 0
            dots = []

            for mi in range(1, duration + 1):
                if mi in inst_map:
                    ins = inst_map[mi]
                    ins_id = str(ins[0])
                    net_due = float(ins[3] or 0.0)
                    paid = actual_paid_by_inst.get(ins_id, float(ins[4] or 0.0))
                    pending = max(0.0, round_curr(net_due - paid))
                    # Self-heal legacy auto-credit bug where pending=0 but paid=0
                    if paid <= 0.01 and net_due > 0.01:
                        pending = net_due
                        is_p = False
                    else:
                        is_p = pending <= 0.01 and (paid > 0 or net_due <= 0.01)

                    if is_p:
                        group_paid_months += 1
                    total_pending_dues += pending
                    dots.append({
                        'month_index': mi,
                        'is_paid': is_p,
                        'is_due': (not is_p and mi <= cur_m),
                        'amount': net_due,
                        'pending': pending
                    })
                else:
                    dots.append({
                        'month_index': mi,
                        'is_paid': False,
                        'is_due': (mi <= cur_m),
                        'amount': 0.0,
                        'pending': 0.0
                    })

            # Calculate fresh cash collected vs non-cash credit settled for this chit group
            group_cash_collected = sum(p['amount'] for p in payments if p['group_id'] == str(g_id) and not p['is_credit_settlement'])
            group_credit_settled = sum(p['amount'] for p in payments if p['group_id'] == str(g_id) and p['is_credit_settlement'])

            months_paid_count += group_paid_months
            total_paid_in += group_cash_collected
            total_credit_settled += group_credit_settled

            # Prior unpaid months / arrears for this membership (mi < cur_m)
            for mi in range(1, cur_m):
                if mi in inst_map:
                    ins = inst_map[mi]
                    ins_id = str(ins[0])
                    net_due = float(ins[3] or 0.0)
                    paid = actual_paid_by_inst.get(ins_id, float(ins[4] or 0.0))
                    pending = max(0.0, round_curr(net_due - paid))
                    if paid <= 0.01 and net_due > 0.01:
                        pending = net_due
                        is_p = False
                    else:
                        is_p = pending <= 0.01 and (paid > 0 or net_due <= 0.01)

                    if not is_p and pending > 0:
                        s_row = sched_map_by_group.get(str(g_id), {}).get(mi)
                        is_closed_sched = (s_row and len(s_row) > 5 and s_row[5] == 'Closed')
                        m_yr_str = format_month_year(ins[2]) or f"Month {mi}"
                        all_unpaid_items.append({
                            'installment_id': ins_id,
                            'membership_id': str(ms_id),
                            'group_id': str(g_id),
                            'group_name': g_name,
                            'group_subtitle': f"₹{int(g_val/100000)}L · {duration}M",
                            'month_index': mi,
                            'month_year': m_yr_str,
                            'amount': pending,
                            'net_due_amount': net_due,
                            'is_closed': is_closed_sched,
                            'tag': f"M{mi} · {m_yr_str} ({'Closed Arrear' if is_closed_sched else 'Prior Due'})",
                            'installment_type': inst_type
                        })

            # Current month installment
            cur_ins = inst_map.get(cur_m)
            if cur_ins:
                c_ins_id = str(cur_ins[0])
                c_net_due = float(cur_ins[3] or 0.0)
                c_paid = actual_paid_by_inst.get(c_ins_id, float(cur_ins[4] or 0.0))
                c_pending = max(0.0, round_curr(c_net_due - c_paid))
                if c_paid <= 0.01 and c_net_due > 0.01:
                    c_pending = c_net_due
                    cur_is_paid = False
                else:
                    cur_is_paid = c_pending <= 0.01 and (c_paid > 0 or c_net_due <= 0.01)

                cur_month_card = {
                    'month_year': format_month_year(cur_ins[2]) or f"Month {cur_m}",
                    'is_paid': cur_is_paid,
                    'pending_amount': c_pending,
                    'paid_amount': c_paid,
                    'net_due_amount': c_net_due,
                    'installment_id': c_ins_id
                }
                if not cur_is_paid and c_pending > 0:
                    all_unpaid_items.append({
                        'installment_id': c_ins_id,
                        'membership_id': str(ms_id),
                        'group_id': str(g_id),
                        'group_name': g_name,
                        'group_subtitle': f"₹{int(g_val/100000)}L · {duration}M",
                        'month_index': cur_m,
                        'month_year': format_month_year(cur_ins[2]) or f"Month {cur_m}",
                        'amount': c_pending,
                        'net_due_amount': c_net_due,
                        'is_closed': False,
                        'tag': f"M{cur_m} · {format_month_year(cur_ins[2]) or f'Month {cur_m}'} (Current Month)",
                        'installment_type': inst_type
                    })
            else:
                cur_month_card = {
                    'month_year': f"Month {cur_m}",
                    'is_paid': False,
                    'pending_amount': 0.0,
                    'paid_amount': 0.0,
                    'net_due_amount': 0.0,
                    'installment_id': None
                }

            # Schedules for payout (pre-fetched in batch)
            sched_rows = sched_rows_by_group.get(str(g_id), [])
            sched_map = sched_map_by_group.get(str(g_id), {})

            if has_lift and lift_m:
                s_row = sched_map.get(lift_m)
                p_amt = float(s_row[2]) * share if s_row else 0.0
                p_loss = float(s_row[1]) * share if s_row else 0.0
                total_paid_out += p_amt
                payout_info = {
                    'has_taken': True,
                    'month_index': lift_m,
                    'month_tag': f"Lifted Month {lift_m}",
                    'label': f"Taken in Month {lift_m}",
                    'amount': p_amt,
                    'loss': p_loss
                }
            else:
                s_row = sched_map.get(cur_m)
                p_amt = float(s_row[2]) * share if s_row else 0.0
                p_loss = float(s_row[1]) * share if s_row else 0.0
                payout_info = {
                    'has_taken': False,
                    'label': 'Not taken',
                    'amount': p_amt,
                    'loss': p_loss
                }

            if inst_type == 'fixed':
                fixed_monthly = round_curr(ce.get_fixed_installment_amount(g_val, duration) * share)
                monthly_disp = fixed_monthly
            else:
                fixed_monthly = None
                monthly_disp = cur_month_card['net_due_amount']

            chits.append({
                'membership_id': str(ms_id),
                'group_id': str(g_id),
                'group_name': g_name,
                'chit_total_value': g_val,
                'duration_months': duration,
                'current_month_index': cur_m,
                'ticket_number': t_num,
                'account_number': acc_no,
                'share_units': share,
                'installment_type': inst_type,
                'fixed_installment_amount': fixed_monthly,
                'is_on_track': cur_month_card['is_paid'],
                'paid_months_count': group_paid_months,
                'remaining_months_count': max(0, duration - group_paid_months),
                'progress_percent': round((group_paid_months / max(1, duration)) * 100),
                'dots': dots,
                'current_month_card': cur_month_card,
                'collected': group_cash_collected,
                'credit_settled': group_credit_settled,
                'total_cleared': group_cash_collected + group_credit_settled,
                'monthly': monthly_disp,
                'available_credit': round_curr(credits_by_grp.get(str(g_id), 0.0)),
                'payout': payout_info
            })

            cur_sched = sched_map.get(cur_m)
            sched_preview = []
            for sr in sched_rows:
                sched_preview.append({
                    'month_index': sr[0],
                    'loss': float(sr[1]) * share,
                    'payout': float(sr[2]) * share,
                    'bonus': float(sr[3]) * share,
                    'kattubadi': float(sr[4]) * share
                })

            payouts_list.append({
                'membership_id': str(ms_id),
                'group_id': str(g_id),
                'group_name': g_name,
                'chit_total_value': g_val,
                'duration_months': duration,
                'current_month_index': cur_m,
                'ticket_number': t_num,
                'account_number': acc_no,
                'share_units': share,
                'has_lifted': bool(has_lift),
                'lifted_month_index': lift_m,
                'payout_amount': (float(sched_map[lift_m][2]) * share) if (has_lift and lift_m in sched_map) else 0.0,
                'loss_amount': (float(sched_map[lift_m][1]) * share) if (has_lift and lift_m in sched_map) else 0.0,
                'current_month_eligible_payout': float(cur_sched[2]) * share if cur_sched else 0.0,
                'current_month_loss': float(cur_sched[1]) * share if cur_sched else 0.0,
                'schedule_preview': sched_preview
            })

        # Activity Log
        activity = []
        for p in payments[:20]:
            activity.append({
                'id': f"act-pay-{p['id']}",
                'type': 'payment',
                'title': 'Payment recorded',
                'amount': p['amount'],
                'group_name': p['group_name'],
                'details': f"{p['month_tag']} · {p['payment_mode']}",
                'time_str': p['time_ago'],
                'actor': get_current_actor(),
                'date': p['payment_date']
            })

        for c in chits:
            activity.append({
                'id': f"act-enr-{c['membership_id']}",
                'type': 'enrollment',
                'title': f"Enrolled in {c['group_name']}",
                'amount': None,
                'group_name': c['group_name'],
                'details': f"Account #{c['account_number']} · {c['share_units']}x share",
                'time_str': 'Earlier',
                'actor': get_current_actor(),
                'date': None
            })

        # Member Payouts for Activity
        cur.execute("""
            SELECT ms.id, ms.lifted_month_index, s.month_year,
                   COALESCE(ms.payout_amount, s.amount_received * ms.share_units, 0),
                   COALESCE(ms.payout_date, s.payout_date),
                   COALESCE(ms.payout_status, s.payout_status),
                   COALESCE(ms.payout_notes, s.notes), g.name as group_name,
                   COALESCE(ms.account_number, ms.ticket_number::text) as account_number, ms.share_units,
                   COALESCE(ms.created_at, s.created_at)
            FROM chit_memberships ms
            JOIN chit_groups g ON ms.chit_group_id = g.id
            LEFT JOIN chit_schedules s ON g.id = s.chit_group_id AND ms.lifted_month_index = s.month_index
            WHERE ms.member_id = %s AND ms.has_lifted = TRUE AND ms.lifted_month_index IS NOT NULL
            ORDER BY COALESCE(ms.payout_date, s.payout_date) DESC NULLS LAST, ms.created_at DESC;
        """, (member_id,))
        for por in cur.fetchall():
            (po_id, po_midx, po_myr, po_amt, po_pdate, po_pstat, po_notes, po_gname, po_acc, po_sh, po_cat) = por
            po_stat = po_pstat or 'unpaid'
            is_p = (po_stat == 'paid')
            d_obj = po_pdate if isinstance(po_pdate, (datetime, date)) else None
            time_str = format_time_ago(po_cat or d_obj)
            activity.append({
                'id': f"act-payout-{po_id}",
                'type': 'payout',
                'title': f"Payout {'disbursed' if is_p else 'recorded'}",
                'amount': float(po_amt or 0),
                'group_name': po_gname,
                'details': f"Month {po_midx} Payout · Account #{po_acc} · {po_sh}x share · {po_stat.upper()}",
                'time_str': time_str,
                'actor': get_current_actor(),
                'date': po_pdate.isoformat() if po_pdate else None
            })

        to_go_amount = max(0.0, (sum(c['chit_total_value'] * c['share_units'] for c in chits)) - (total_paid_in + total_credit_settled))
        to_go_months = max(0, total_months_count - months_paid_count)

        # Member Loans
        cur.execute("""
            SELECT id::text, principal_amount, annual_interest_rate, compounding_frequency,
                   disbursal_date::text, status, total_repaid_principal, total_repaid_interest,
                   settled_at::text, settlement_type, notes, created_at::text
            FROM chit_loans
            WHERE member_id = %s
            ORDER BY disbursal_date DESC, created_at DESC;
        """, (member_id,))
        loan_rows = cur.fetchall()
        member_loans = []
        tot_active_loan_balance = 0.0
        tot_active_loan_principal = 0.0
        tot_active_loan_accrued_interest = 0.0

        # Batch-fetch repayments for all member loans (eliminates N+1 query)
        loan_ids = [str(lr[0]) for lr in loan_rows]
        repayments_by_loan = defaultdict(list)
        if loan_ids:
            cur.execute("""
                SELECT loan_id::text, id::text, repayment_date::text, principal_amount, interest_amount, total_amount, payment_mode, receipt_no, notes
                FROM chit_loan_repayments
                WHERE loan_id::text = ANY(%s)
                ORDER BY repayment_date DESC;
            """, (loan_ids,))
            for rp in cur.fetchall():
                repayments_by_loan[rp[0]].append({
                    'id': rp[1], 'date': rp[2], 'principal': float(rp[3] or 0),
                    'interest': float(rp[4] or 0), 'total': float(rp[5] or 0),
                    'mode': rp[6], 'receipt_no': rp[7] or '', 'notes': rp[8] or ''
                })

        for lr in loan_rows:
            calc = calculate_loan_compound_interest(
                principal=lr[1],
                annual_rate=lr[2],
                disbursal_date=lr[4],
                repaid_principal=lr[6],
                repaid_interest=lr[7]
            )
            if lr[5] == 'active':
                tot_active_loan_balance += calc['total_payoff']
                tot_active_loan_principal += calc['remaining_principal']
                tot_active_loan_accrued_interest += calc['accrued_interest']

            repayments = repayments_by_loan.get(str(lr[0]), [])

            member_loans.append({
                'id': lr[0],
                'principal': float(lr[1] or 0),
                'rate': float(lr[2] or 0),
                'compounding_frequency': lr[3] or 'yearly',
                'disbursal_date': lr[4],
                'status': lr[5],
                'repaid_principal': float(lr[6] or 0),
                'repaid_interest': float(lr[7] or 0),
                'settled_at': lr[8],
                'settlement_type': lr[9],
                'notes': lr[10] or '',
                'calculation': calc,
                'repayments': repayments
            })

            d_dt = None
            if lr[4]:
                try: d_dt = datetime.fromisoformat(lr[4])
                except Exception: pass
            activity.append({
                'id': f"act-loan-{lr[0]}",
                'type': 'loan',
                'title': f"Loan Disbursed ({lr[5].upper()})",
                'amount': float(lr[1] or 0),
                'group_name': 'Member Loan',
                'details': f"₹{float(lr[1]):,.0f} @ {lr[2]}% p.a. · Current payoff: ₹{calc['total_payoff']:,.0f}",
                'time_str': format_time_ago(d_dt),
                'actor': get_current_actor(),
                'date': lr[4]
            })

        total_due_now_payable = sum(x['amount'] for x in all_unpaid_items)
        if total_due_now_payable > 0 and all_unpaid_items:
            first_unpaid = all_unpaid_items[0]
            current_pending = sum(x['amount'] for x in all_unpaid_items if not x['is_closed'])
            arrears_pending = sum(x['amount'] for x in all_unpaid_items if x['is_closed'])
            first_ms_id = first_unpaid['membership_id']
            due_now_item = {
                'amount': total_due_now_payable,
                'current_month_pending': current_pending,
                'arrears_pending': arrears_pending,
                'breakdown': all_unpaid_items,
                'month_year': first_unpaid['month_year'],
                'month_index': first_unpaid['month_index'],
                'chit_name': first_unpaid['group_name'],
                'group_subtitle': f"{len(all_unpaid_items)} cycle{'s' if len(all_unpaid_items) > 1 else ''} pending",
                'installment_id': first_unpaid['installment_id'],
                'membership_id': first_ms_id,
                'net_due_amount': total_due_now_payable,
                'installment_type': first_unpaid.get('installment_type', 'incremental'),
                'available_credit': round_curr(credits_by_ms.get(str(first_ms_id), 0.0))
            }

        is_defaulted = bool(mrow[13])
        defaulted_manually = bool(mrow[14])
        defaulted_reason = mrow[15] or ''
        defaulted_at = mrow[16]

        closed_missed_count = sum(1 for x in all_unpaid_items if x['is_closed'])
        if not defaulted_manually:
            if closed_missed_count >= 3:
                is_defaulted = True
                defaulted_reason = f'Skipped {closed_missed_count} repayments in closed cycles'
            elif is_defaulted and closed_missed_count < 3:
                is_defaulted = False
                defaulted_reason = ''

        return jsonify({
            'member': {
                'id': str(mrow[0]),
                'customer_id': mrow[12] or '',
                'full_name': mrow[1],
                'phone': mrow[2] or '',
                'email': mrow[3] or '',
                'address': mrow[4] or '',
                'govt_id_last4': mrow[6] or '',
                'member_portal_enabled': bool(mrow[7]),
                'nominee_name': mrow[8] or '',
                'nominee_phone': mrow[9] or '',
                'nominee_relation': mrow[10] or '',
                'created_at': mrow[11].isoformat() if mrow[11] else None,
                'is_defaulted': is_defaulted,
                'defaulted_manually': defaulted_manually,
                'defaulted_reason': defaulted_reason,
                'defaulted_at': defaulted_at.isoformat() if defaulted_at else None,
                'linked_group_id': str(mrow[17]) if mrow[17] else None,
                'linked_count': len(linked_members)
            },
            'linked_members': linked_members,
            'linked_group_id': str(mrow[17]) if mrow[17] else None,
            'analytics': {
                'active_chits_count': len(chits),
                'total_dues': total_pending_dues,
                'accumulated_due_now': total_due_now_payable,
                'available_credit': credit_wallet.get('total_available_credit', 0.0),
                'credit_settled': total_credit_settled,
                'total_cleared': total_paid_in + total_credit_settled,
                'is_defaulted': is_defaulted,
                'defaulted_reason': defaulted_reason,
                'due_breakdown': all_unpaid_items,
                'net_balance': f"-₹{int(total_pending_dues):,}" if total_pending_dues > 0 else "₹0 net",
                'portal_status': 'On' if mrow[7] else 'Off',
                'due_now': due_now_item,
                'paid_in': total_paid_in,
                'paid_out': total_paid_out,
                'to_go': to_go_amount,
                'to_go_months': to_go_months,
                'months_paid_count': months_paid_count,
                'total_months_count': total_months_count,
                'progress_percent': round((months_paid_count / max(1, total_months_count)) * 100),
                'active_loans_count': len([l for l in member_loans if l['status'] == 'active']),
                'total_loan_balance': round_curr(tot_active_loan_balance),
                'total_loan_principal': round_curr(tot_active_loan_principal),
                'total_loan_interest': round_curr(tot_active_loan_accrued_interest)
            },
            'chits': chits,
            'payments': payments,
            'payments_summary': {
                'total_collected': total_paid_in,
                'total_credit_settled': total_credit_settled,
                'total_cleared': total_paid_in + total_credit_settled,
                'total_payouts': total_paid_out,
                'total_penalties': 0.0,
                'count': len(payments)
            },
            'credit_wallet': credit_wallet,
            'payouts': payouts_list,
            'loans': member_loans,
            'activity': activity
        })
    except Exception as e:
        logger.error(f"[CHIT_MEMBER_FOLIO] Error loading folio for member {member_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to load member folio', 'details': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/members/<member_id>', methods=['GET', 'PUT'])
def member_detail_or_update(member_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        if request.method == 'GET':
            cur.execute("""
                SELECT id, COALESCE(customer_id, '') as customer_id, full_name, phone, email, address,
                       COALESCE(govt_id_type, 'Aadhaar') as govt_id_type,
                       COALESCE(govt_id_number, '') as govt_id_number,
                       COALESCE(govt_id_last4, '') as govt_id_last4,
                       COALESCE(member_portal_enabled, TRUE) as member_portal_enabled,
                       COALESCE(nominee_name, '') as nominee_name,
                       COALESCE(nominee_phone, '') as nominee_phone,
                       COALESCE(nominee_relation, '') as nominee_relation
                FROM chit_members
                WHERE id = %s;
            """, (member_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Member not found'}), 404
            return jsonify({
                'id': str(row[0]),
                'customer_id': row[1],
                'full_name': row[2],
                'phone': row[3] or '',
                'email': row[4] or '',
                'address': row[5] or '',
                'govt_id_type': row[6] or 'Aadhaar',
                'govt_id_number': row[7] or '',
                'govt_id_last4': row[8] or '',
                'member_portal_enabled': bool(row[9]),
                'nominee_name': row[10] or '',
                'nominee_phone': row[11] or '',
                'nominee_relation': row[12] or ''
            })

        data = request.get_json() or {}
        full_name = (data.get('full_name') or '').strip()
        phone = (data.get('phone') or '').strip()
        email = (data.get('email') or '').strip()
        address = (data.get('address') or '').strip()
        govt_id_type = (data.get('govt_id_type') or 'Aadhaar').strip()
        govt_id_number = (data.get('govt_id_number') or '').strip()
        govt_id_last4 = (data.get('govt_id_last4') or '').strip()
        if govt_id_number and not govt_id_last4:
            govt_id_last4 = govt_id_number[-4:] if len(govt_id_number) >= 4 else govt_id_number
        portal_enabled = bool(data.get('member_portal_enabled', data.get('portal_enabled', True)))
        nominee_name = (data.get('nominee_name') or '').strip()
        nominee_phone = (data.get('nominee_phone') or '').strip()
        nominee_relation = (data.get('nominee_relation') or '').strip()
        cust_id = (data.get('customer_id') or '').strip()

        if not full_name:
            return jsonify({'error': 'Full name is required'}), 400

        if cust_id:
            if not (len(cust_id) == 5 and cust_id.isdigit()):
                return jsonify({'error': 'Customer ID must be exactly 5 digits (e.g. 10001)'}), 400
            cur.execute("SELECT id FROM chit_members WHERE customer_id = %s AND id != %s;", (cust_id, member_id))
            if cur.fetchone():
                return jsonify({'error': f"Customer ID '{cust_id}' is already in use by another subscriber."}), 400
            cur.execute("UPDATE chit_members SET customer_id = %s WHERE id = %s;", (cust_id, member_id))

        cur.execute("""
            UPDATE chit_members
            SET full_name = %s, phone = %s, email = %s, address = %s,
                govt_id_type = %s, govt_id_number = %s, govt_id_last4 = %s,
                member_portal_enabled = %s,
                nominee_name = %s, nominee_phone = %s, nominee_relation = %s
            WHERE id = %s;
        """, (full_name, phone, email, address,
              govt_id_type, govt_id_number, govt_id_last4,
              portal_enabled, nominee_name, nominee_phone, nominee_relation, member_id))
        conn.commit()

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (get_current_actor(), get_current_actor_role(), 'MEMBER_PROFILE_UPDATED', 'MEMBER', member_id,
              json.dumps({'full_name': full_name, 'phone': phone, 'customer_id': cust_id})))
        conn.commit()

        return jsonify({'success': True, 'message': 'Subscriber profile updated successfully'})
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/members/<member_id>/payout', methods=['POST'])
def record_member_payout(member_id):
    data = request.get_json() or {}
    membership_id = data.get('membership_id')
    month_index = int(data.get('month_index', 1))

    if not membership_id:
        return jsonify({'error': 'Membership ID is required'}), 400

    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT chit_group_id FROM chit_memberships WHERE id = %s AND member_id = %s;", (membership_id, member_id))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Membership not found for this subscriber'}), 404
        chit_id = str(row[0])
    finally:
        cur.close()
        conn.close()

    return handle_month_payout(chit_id, month_index)

@chit_bp.route('/api/members/<member_id>', methods=['DELETE'])
def delete_member(member_id):
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*) FROM chit_payments p
            JOIN chit_memberships ms ON p.membership_id = ms.id
            WHERE ms.member_id = %s;
        """, (member_id,))
        p_count = cur.fetchone()[0]
        if p_count > 0:
            return jsonify({'error': f'Cannot delete subscriber with {p_count} existing payment record(s). Please delete or reverse payment records first.'}), 400

        cur.execute("""
            DELETE FROM chit_installments WHERE membership_id IN (
                SELECT id FROM chit_memberships WHERE member_id = %s
            );
        """, (member_id,))
        cur.execute("DELETE FROM chit_memberships WHERE member_id = %s;", (member_id,))
        cur.execute("DELETE FROM chit_members WHERE id = %s;", (member_id,))
        conn.commit()

        cur.execute("""
            INSERT INTO chit_audit_logs (actor_name, actor_role, action, entity_type, entity_id, details)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (get_current_actor(), get_current_actor_role(), 'MEMBER_DELETED', 'MEMBER', member_id, json.dumps({'deleted_member_id': member_id})))
        conn.commit()

        return jsonify({'success': True, 'message': 'Subscriber deleted successfully'})
    finally:
        cur.close()
        conn.close()

@chit_bp.route('/api/activity', methods=['GET'])
def get_activity_log():
    conn = get_pg_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, actor_name, actor_role, action, entity_type, entity_id, details, created_at
            FROM chit_audit_logs
            ORDER BY created_at DESC
            LIMIT 50;
        """)
        rows = cur.fetchall()
        logs = []
        for r in rows:
            logs.append({
                'id': str(r[0]),
                'actor_name': r[1],
                'actor_role': r[2],
                'action': r[3],
                'entity_type': r[4],
                'entity_id': r[5],
                'details': r[6],
                'created_at': r[7].isoformat() if r[7] else None
            })
        return jsonify(logs)
    finally:
        cur.close()
        conn.close()
