from db import get_pg_connection

def get_dashboard_totals(vid, eid=None):
    conn = get_pg_connection()
    cur = conn.cursor()

    if eid:
        cur.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(c.total_amount), 0),
                COALESCE(SUM(c.paid_amount), 0),
                COALESCE(SUM(c.balance_amount), 0)
            FROM customer c
            JOIN village v ON v.vid = c.vid
            WHERE c.vid = %s
              AND (v.emp1 = %s OR v.emp2 = %s)
        """, (vid, eid, eid))
    else:
        cur.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(total_amount), 0),
                COALESCE(SUM(paid_amount), 0),
                COALESCE(SUM(balance_amount), 0)
            FROM customer
            WHERE vid = %s
        """, (vid,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        row = (0, 0, 0, 0)

    return {
        "total_customers": int(row[0]),
        "sum_amt": float(row[1]),
        "sum_pamt": float(row[2]),
        "sum_bamt": float(row[3]),
    }