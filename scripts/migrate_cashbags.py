import db

conn = db.get_pg_connection()
cur = conn.cursor()

# 1. Create table
cur.execute("""
    CREATE TABLE IF NOT EXISTS village_cashbags (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        emp1 INT NOT NULL,
        emp2 INT,
        name VARCHAR(150) NOT NULL,
        village_codes TEXT[] NOT NULL DEFAULT '{}',
        week_ending_day INT DEFAULT 3,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_village_cashbags_emp ON village_cashbags(emp1, emp2);
""")
conn.commit()

# 2. Check if already seeded
cur.execute("SELECT COUNT(*) FROM village_cashbags")
cnt = cur.fetchone()[0]
print(f"Current village_cashbags count: {cnt}")

if cnt == 0:
    # Fetch all active employee pairs
    cur.execute("""
        SELECT v.emp1, v.emp2, array_agg(v.village_code ORDER BY v.village_code)
        FROM village v
        WHERE v.status = 'active'
        GROUP BY v.emp1, v.emp2
    """)
    pairs = cur.fetchall()

    for emp1, emp2, vcodes in pairs:
        if emp1 == 63 and (emp2 is None or emp2 == emp1):
            # Special case for Sappa Venkata Kalyan
            # Cashbag 1: PGR/PRG, SDNR, NGKL2, BTPR, KLPR2
            # Cashbag 2: BTPR2-M, KLPR3-M, NGKL3-M, SDNR2-M
            cb1_codes = [c for c in ['PRG', 'PGR', 'SDNR', 'NGKL2', 'BTPR', 'KLPR2'] if c in vcodes]
            cb2_codes = [c for c in ['BTPR2-M', 'KLPR3-M', 'NGKL3-M', 'SDNR2-M'] if c in vcodes]

            cur.execute("""
                INSERT INTO village_cashbags (emp1, emp2, name, village_codes, week_ending_day)
                VALUES (%s, %s, %s, %s, 3)
            """, (emp1, emp2, "Main", cb1_codes))

            cur.execute("""
                INSERT INTO village_cashbags (emp1, emp2, name, village_codes, week_ending_day)
                VALUES (%s, %s, %s, %s, 3)
            """, (emp1, emp2, "Route M", cb2_codes))
            print("Seeded Sappa Venkata Kalyan 2 cashbags: Main and Route M")
        else:
            cur.execute("""
                INSERT INTO village_cashbags (emp1, emp2, name, village_codes, week_ending_day)
                VALUES (%s, %s, %s, %s, 3)
            """, (emp1, emp2, "Main Cashbag", vcodes))

    conn.commit()
    print("Seeded default cashbags for all pairs.")

cur.execute("SELECT id, emp1, emp2, name, village_codes FROM village_cashbags WHERE emp1 = 63")
for row in cur.fetchall():
    print("Emp 63 Cashbag:", row)

cur.close()
conn.close()
