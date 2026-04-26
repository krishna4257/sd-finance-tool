import psycopg2
from psycopg2 import sql
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

MIGRATION_TABLES = [
    "employee",
    "village",
    "customer",
    "closed_cust_account",
    "payment",
    "closed_cust_payment",
]

# These tables are needed for login and user access. They can be truncated by
# TRUNCATE ... CASCADE when users references employee or village data.
PRESERVE_TARGET_TABLES = [
    "users",
    "user_devices",
    "user_village_access",
]


# =========================
# HELPERS
# =========================

def table_exists(cur, table):
    cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
    return cur.fetchone()[0] is not None


def table_row_count(cur, table):
    cur.execute(
        sql.SQL("SELECT COUNT(*) FROM public.{}").format(sql.Identifier(table))
    )
    return cur.fetchone()[0]


def temp_table_row_count(cur, table):
    cur.execute(
        sql.SQL("SELECT COUNT(*) FROM pg_temp.{}").format(sql.Identifier(table))
    )
    return cur.fetchone()[0]


def get_insertable_columns(cur, table):
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND is_generated = 'NEVER'
        ORDER BY ordinal_position
    """, (table,))
    return [row[0] for row in cur.fetchall()]


def table_has_always_identity(cur, table):
    cur.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND identity_generation = 'ALWAYS'
        )
    """, (table,))
    return cur.fetchone()[0]


def sync_owned_sequences(cur, table):
    cur.execute("""
        SELECT column_name, pg_get_serial_sequence(%s, column_name)
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
    """, (f"public.{table}", table))

    for column, sequence_name in cur.fetchall():
        if not sequence_name:
            continue

        cur.execute(
            sql.SQL("SELECT MAX({}) FROM public.{}").format(
                sql.Identifier(column),
                sql.Identifier(table),
            )
        )
        max_value = cur.fetchone()[0]

        if max_value is None:
            cur.execute("SELECT setval(%s::regclass, 1, false)", (sequence_name,))
        else:
            cur.execute(
                "SELECT setval(%s::regclass, %s, true)",
                (sequence_name, max_value),
            )


def backup_preserved_tables(cur):
    if not TRUNCATE_TARGET:
        return {}

    print("\n🛟 Backing up login/access tables before target truncation")
    backups = {}

    for table in PRESERVE_TARGET_TABLES:
        if not table_exists(cur, table):
            print(f"⚠️ Skipping backup for {table} (does not exist on target)")
            continue

        backup_table = f"_prod_migration_backup_{table}"
        cur.execute(
            sql.SQL("CREATE TEMP TABLE {} AS SELECT * FROM public.{}").format(
                sql.Identifier(backup_table),
                sql.Identifier(table),
            )
        )

        backups[table] = backup_table
        print(f"🛟 {table}: preserved {temp_table_row_count(cur, backup_table)} rows")

    return backups


def restore_preserved_tables(cur, backups):
    if not backups:
        return

    print("\n🛟 Restoring preserved login/access tables")

    for table in PRESERVE_TARGET_TABLES:
        backup_table = backups.get(table)

        if not backup_table or not table_exists(cur, table):
            continue

        backup_count = temp_table_row_count(cur, backup_table)
        current_count = table_row_count(cur, table)

        if backup_count == 0:
            print(f"ℹ️ {table}: backup was empty")
            sync_owned_sequences(cur, table)
            continue

        if current_count > 0:
            print(f"ℹ️ {table}: still has {current_count} rows; left unchanged")
            sync_owned_sequences(cur, table)
            continue

        columns = get_insertable_columns(cur, table)
        if not columns:
            print(f"⚠️ {table}: no insertable columns found; skipped restore")
            continue

        column_list = sql.SQL(", ").join(sql.Identifier(column) for column in columns)
        overriding = (
            sql.SQL("OVERRIDING SYSTEM VALUE")
            if table_has_always_identity(cur, table)
            else sql.SQL("")
        )

        cur.execute(
            sql.SQL("""
                INSERT INTO public.{table} ({columns})
                {overriding}
                SELECT {columns}
                FROM pg_temp.{backup_table}
                ON CONFLICT DO NOTHING
            """).format(
                table=sql.Identifier(table),
                columns=column_list,
                overriding=overriding,
                backup_table=sql.Identifier(backup_table),
            )
        )

        print(f"✅ {table}: restored {cur.rowcount} rows")
        sync_owned_sequences(cur, table)


def truncate(cur, table):
    print(f"🧹 Truncating {table}")

    if not table_exists(cur, table):
        print(f"⚠️ Skipping {table} (does not exist on target)")
        return

    cur.execute(
        sql.SQL("TRUNCATE TABLE public.{} CASCADE").format(sql.Identifier(table))
    )


def copy_table(src_cur, tgt_cur, select_sql, insert_sql, label):
    print(f"🚀 Migrating {label}")

    if not table_exists(tgt_cur, label):
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


def print_final_counts(cur):
    print("🔍 Final row counts:")

    for table in MIGRATION_TABLES:
        if not table_exists(cur, table):
            print(f"{table}: ❌ table not found on target")
            continue

        if table == "payment":
            cur.execute("SELECT COUNT(*) FROM public.payment WHERE cid IS NOT NULL")
            print(f"{table}: {cur.fetchone()[0]}")
            continue

        print(f"{table}: {table_row_count(cur, table)}")

    for table in PRESERVE_TARGET_TABLES:
        if table_exists(cur, table):
            print(f"{table}: {table_row_count(cur, table)} (preserved)")


def main():
    src = None
    tgt = None
    src_cur = None
    tgt_cur = None

    try:
        src = psycopg2.connect(**SOURCE_DB)
        tgt = psycopg2.connect(**TARGET_DB)

        src.autocommit = True
        tgt.autocommit = False

        src_cur = src.cursor()
        tgt_cur = tgt.cursor()

        backups = backup_preserved_tables(tgt_cur)

        # =========================
        # 1️⃣ EMPLOYEE
        # =========================

        if TRUNCATE_TARGET:
            truncate(tgt_cur, "employee")

        copy_table(
            src_cur,
            tgt_cur,
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
            truncate(tgt_cur, "village")

        copy_table(
            src_cur,
            tgt_cur,
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
            truncate(tgt_cur, "customer")

        copy_table(
            src_cur,
            tgt_cur,
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
            truncate(tgt_cur, "closed_cust_account")

        copy_table(
            src_cur,
            tgt_cur,
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
            truncate(tgt_cur, "payment")

        copy_table(
            src_cur,
            tgt_cur,
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
            truncate(tgt_cur, "closed_cust_payment")

        copy_table(
            src_cur,
            tgt_cur,
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

        restore_preserved_tables(tgt_cur, backups)
        print_final_counts(tgt_cur)

        tgt.commit()
        print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY")

    except Exception:
        if tgt:
            tgt.rollback()
            print("\n❌ Migration failed. Target database changes were rolled back.")
        raise

    finally:
        if src_cur:
            src_cur.close()
        if tgt_cur:
            tgt_cur.close()
        if src:
            src.close()
        if tgt:
            tgt.close()


if __name__ == "__main__":
    main()
