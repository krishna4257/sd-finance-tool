from werkzeug.security import generate_password_hash
from db import get_pg_connection

def create_admin():
    password = "Jaya@3579"

    # 👇 FORCE PBKDF2 instead of scrypt
    hashed = generate_password_hash(
        password,
        method="pbkdf2:sha256",
        salt_length=16
    )

    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (username, password_hash, employee_id, is_admin)
        VALUES (%s, %s, %s, %s)
    """, ("jayakrishna", hashed, 6, True))

    conn.commit()
    cur.close()
    conn.close()

    print("Admin created successfully")

if __name__ == "__main__":
    create_admin()