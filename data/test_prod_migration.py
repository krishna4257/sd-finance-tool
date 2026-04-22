import psycopg2
from psycopg2.extras import execute_values

# =========================
# CONFIG
# =========================

SOURCE_DB = {
    "host": "localhost",
    "port": 5433,
    "dbname": "template1",          # staging DB on Mac
    "user": "jayakrishnareddykarri",
    "password": "Jaya@3579"
}

TARGET_DB = {
    "host": "192.168.1.65",
    "port": 5432,
    "dbname": "sd_finance",
    "user": "sd_user",
    "password": "Jaya@3579"
}

BATCH_SIZE = 50_000
TRUNCATE_TARGET = True   # set False if you want append-only

# =========================
# CONNECTIONS
# =========================

src = psycopg2.connect(**SOURCE_DB)
tgt = psycopg2.connect(**TARGET_DB)

src.autocommit = True
tgt.autocommit = True

src_cur = src.cursor()
tgt_cur = tgt.cursor()

# =========================
# HELPERS
# =========================

def truncate(table):
    print(f"🧹 Truncating {table}")
    
    # Check if table exists
    tgt_cur.execute(f"SELECT to_regclass('public.{table}')")
    exists = tgt_cur.fetchone()[0]
    
    if not exists:
        print(f"⚠️ Skipping {table} (does not exist on target)")
        return
    
    tgt_cur.execute(f"TRUNCATE TABLE public.{table} CASCADE")

def copy_table(select_sql, insert_sql, label):
    print(f"🚀 Migrating {label}")
    
    # Check if target table exists
    tgt_cur.execute(f"SELECT to_regclass('public.{label}')")
    exists = tgt_cur.fetchone()[0]
    
    if not exists:
        print(f"⚠️ Skipping {label} (target table not found)")
        return
    
    # Ensure deterministic order to avoid FK issues (customer before payment references)
    if "FROM payment" in select_sql or "FROM closed_cust_payment" in select_sql:
        select_sql = select_sql.strip() + " ORDER BY cid"
    src_cur.execute(select_sql)

    total = 0
    while True:
        rows = src_cur.fetchmany(BATCH_SIZE)
        if not rows:
            break

        execute_values(tgt_cur, insert_sql, rows)
        total += len(rows)
        print(f"   → {total} rows")

    print(f"✅ {label} done: {total} rows\n")

# =========================
# 1️⃣ EMPLOYEE
# =========================

if TRUNCATE_TARGET:
    truncate("employee")

copy_table(
    """
    SELECT eid, name, phone_number, city, joining_date, level, state, created_at
    FROM stage_employee
    """,
    """
    INSERT INTO public.employee (
        eid, name, phone_number, city, joining_date, level, state, created_at
    ) VALUES %s
    """,
    "employee"
)

# =========================
# 2️⃣ VILLAGE
# =========================

if TRUNCATE_TARGET:
    truncate("village")

copy_table(
    """
    SELECT vid, village_code, village_name, district, pincode,
           state, emp1, emp2, created_at, source_file
    FROM stage_village
    """,
    """
    INSERT INTO public.village (
        vid, village_code, village_name, district, pincode,
        state, emp1, emp2, created_at, source_file
    ) VALUES %s
    """,
    "village"
)

# =========================
# 3️⃣ CUSTOMER
# =========================

if TRUNCATE_TARGET:
    truncate("customer")

copy_table(
    """
    SELECT cid, ano, name, vid, start_date, end_date,
           total_amount, paid_amount, balance_amount,
           installment_amount, type, period, pano,
           created_at, aadhaar_number, notes, latitude,
           longitude, eid
    FROM customer
    """,
    """
    INSERT INTO public.customer (
        cid, ano, name, vid, start_date, end_date,
        total_amount, paid_amount, balance_amount,
        installment_amount, type, period, pano,
        created_at, aadhaar_number, notes, latitude,
        longitude, eid
    ) VALUES %s
    """,
    "customer"
)

# =========================
# 3️⃣B CLOSED CUSTOMER ACCOUNT
# =========================

if TRUNCATE_TARGET:
    truncate("closed_cust_account")

copy_table(
    """
    SELECT cid, ano, name, vid, start_date, end_date,
           total_amount, paid_amount, balance_amount,
           installment_amount, type, period, pano,
           created_at, aadhaar_number, notes, latitude,
           longitude, eid, status
    FROM closed_cust_account
    """,
    """
    INSERT INTO public.closed_cust_account (
        cid, ano, name, vid, start_date, end_date,
        total_amount, paid_amount, balance_amount,
        installment_amount, type, period, pano,
        created_at, aadhaar_number, notes, latitude,
        longitude, eid, status
    ) VALUES %s
    """,
    "closed_cust_account"
)

# =========================
# 4️⃣ PAYMENT
# =========================

if TRUNCATE_TARGET:
    truncate("payment")

copy_table(
    """
    SELECT pid, ano, payment_date, amt, created_at, eid, cid, vid
    FROM payment
    """,
    """
    INSERT INTO public.payment (
        pid, ano, payment_date, amt, created_at, eid, cid, vid
    ) OVERRIDING SYSTEM VALUE VALUES %s
    """,
    "payment"
)

# =========================
# 5️⃣ CLOSED / OLD PAYMENTS
# =========================

if TRUNCATE_TARGET:
    truncate("closed_cust_payment")

copy_table(
    """
    SELECT pid, ano, payment_date, amt, source_file,
           created_at, eid, cid, vid
    FROM closed_cust_payment
    """,
    """
    INSERT INTO public.closed_cust_payment (
        pid, ano, payment_date, amt, source_file,
        created_at, eid, cid, vid
    ) OVERRIDING SYSTEM VALUE VALUES %s
    """,
    "closed_cust_payment"
)

# =========================
# VALIDATION
# =========================

print("🔍 Final row counts:")

for table in [
    "employee",
    "village",
    "customer",
    "closed_cust_account",
    "payment",
    "closed_cust_payment"
]:
    tgt_cur.execute(f"SELECT to_regclass('public.{table}')")
    exists = tgt_cur.fetchone()[0]

    if not exists:
        print(f"{table}: ❌ table not found on target")
        continue

    if table == "payment":
        tgt_cur.execute("SELECT COUNT(*) FROM public.payment WHERE cid IS NOT NULL")
        print(f"{table}: {tgt_cur.fetchone()[0]}")
        continue

    tgt_cur.execute(f"SELECT COUNT(*) FROM public.{table}")
    print(f"{table}: {tgt_cur.fetchone()[0]}")

print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY")

src_cur.close()
tgt_cur.close()
src.close()
tgt.close()