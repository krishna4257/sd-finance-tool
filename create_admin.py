# create_admin.py

import os
import sqlite3
from werkzeug.security import generate_password_hash
from database_manager import download_from_gcs, upload_to_gcs

def create_admin():
    # Store auth DB inside project folder
    project_root = os.path.dirname(os.path.abspath(__file__))
    db_folder = os.path.join(project_root, "local_auth")
    os.makedirs(db_folder, exist_ok=True)

    local_path = os.path.join(db_folder, "auth.sqlite")
    print("Using local auth DB at:", local_path)

    # Try loading existing DB from GCS
    try:
        download_from_gcs("auth.sqlite", local_path) # type: ignore
        print("Downloaded existing auth.sqlite from GCS")
    except:
        print("No auth DB found in GCS. Creating new one locally.")

    conn = sqlite3.connect(local_path)
    c = conn.cursor()

    # Ensure USERS table exists
    c.execute("""
        CREATE TABLE IF NOT EXISTS USERS(
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            system_id TEXT,
            notes TEXT
        )
    """)

    print("\n--- Create / Update Admin User ---")
    user = input("Enter admin username: ").strip()
    pw = input("Enter admin password: ").strip()
    system_id = input("Enter authorized system ID (optional): ").strip()
    notes = input("Notes (optional): ").strip()

    # FIX: Force use of pbkdf2 so scrypt is NOT used
    hash_pw = generate_password_hash(pw, method="pbkdf2:sha256")

    # Insert or update
    c.execute(
        "INSERT OR REPLACE INTO USERS (username, password_hash, system_id, notes) VALUES (?, ?, ?, ?)",
        (user, hash_pw, system_id, notes)
    )

    conn.commit()
    conn.close()

    # Upload new auth DB to GCS
    upload_to_gcs(local_path, "auth.sqlite")

    print("\nAdmin created & uploaded successfully.")

if __name__ == "__main__":
    create_admin()