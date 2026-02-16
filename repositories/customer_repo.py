from db import get_pg_connection

def get_customer_info_by_ano(ano, vid):
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            name,
            total_amount,
            paid_amount,
            balance_amount,
            installment_amount
        FROM customer
        WHERE ano = %s AND vid = %s
    """, (ano, vid))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "name": row[0],
        "amt": float(row[1] or 0),
        "pamt": float(row[2] or 0),
        "bamt": float(row[3] or 0),
        "da": float(row[4] or 0)
    }

def get_all_customers_by_context(eid, vid):
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
  cid,
  ano,
  name,
  vid,
  start_date,
  end_date,
  total_amount,
  paid_amount,
  balance_amount,
  installment_amount,
  type,
  period,
  pano,
  created_at,
  aadhar_number,
  notes,
  latitude,
  longitude,
  eid
FROM customer
WHERE eid = %s AND vid = %s
ORDER BY ano;
    """, (eid, vid))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    customers = []
    for r in rows:
        customers.append({
            "cid": r[0],
            "ano": r[1],
            "name": r[2],
            "vid": r[3],
            "start_date": r[4],
            "end_date": r[5],
            "total_amount": float(r[6] or 0),
            "paid_amount": float(r[7] or 0),
            "balance_amount": float(r[8] or 0),
            "installment_amount": float(r[9] or 0),
            "type": r[10],
            "period": r[11],
            "pano": r[12],
            "created_at": r[13],
            "aadhar_number": r[14],
            "notes": r[15],
            "latitude": r[16],
            "longitude": r[17],
            "eid": r[18]
        })

    return customers


def customer_exists_by_ano(ano: int) -> bool:
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM customer WHERE ano = %s LIMIT 1", (ano,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists


def get_highest_ano() -> int:
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(CAST(ano AS INTEGER)) FROM customer;")
    result = cur.fetchone()
    highest = result[0] if result else 0
    cur.close()
    conn.close()
    return highest

def get_highest_ano_by_vid(vid):
    conn = get_pg_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(MAX(CAST(ano AS INTEGER)), 0)
        FROM customer
        WHERE vid = %s
    """, (vid,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 0

def ano_exists(ano, vid):
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM customer
                WHERE ano = %s AND vid = %s
                LIMIT 1
            """, (ano, vid))
            return cur.fetchone() is not None

def insert_customer(data):
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO customer (
                    ano, name, pano, vid, eid,
                    start_date, end_date,
                    total_amount, paid_amount, balance_amount, installment_amount,
                    type, period,
                    aadhar_number, notes,
                    latitude, longitude
                )
                VALUES (
                    %(ano)s, %(name)s, %(pano)s, %(vid)s, %(eid)s,
                    %(start_date)s, %(end_date)s,
                    %(total_amount)s, %(paid_amount)s, %(balance_amount)s, %(installment_amount)s,
                    %(type)s, %(period)s,
                    %(aadhar_number)s, %(notes)s,
                    %(latitude)s, %(longitude)s
                )
                RETURNING cid
            """, data)

            result = cur.fetchone()
            if result is None:
                conn.close()
                return None
            cid = result[0]
            conn.commit()
            return cid


def customer_exists_by_ano_and_vid(ano, vid):
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM customer
        WHERE ano = %s AND vid = %s
        LIMIT 1
    """, (ano, vid))

    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists