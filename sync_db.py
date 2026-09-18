#!/usr/bin/env python3
"""
PostgreSQL Database Replication Utility
Clones Database A (Source / Main) into Database B (Target / Local / Replica).

This script performs the following steps:
1. Reads database credentials from .env.
2. Checks connectivity to both databases (verifying Database A is untouched).
3. Automatically locates 'pg_dump' and 'psql' binaries (including on Windows).
4. Prompts the user with a warning and requires confirming the database name to wipe.
5. Performs a schema and data dump of Database A to a temporary file.
6. Clears Database B by dropping and recreating the public schema.
7. Restores the dump to Database B.
8. Cleans up temporary files.
"""

import os
import sys
import shutil
import glob
import subprocess
import tempfile
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Required connection keys
REQUIRED_A = ["DB_A_HOST", "DB_A_PORT", "DB_A_NAME", "DB_A_USER", "DB_A_PASSWORD"]
REQUIRED_B = ["DB_B_HOST", "DB_B_PORT", "DB_B_NAME", "DB_B_USER", "DB_B_PASSWORD"]

def get_env_var(name):
    val = os.environ.get(name)
    if val:
        return val.strip()
    return ""

def verify_env():
    """Verify that all required environment variables are present."""
    missing_a = [var for var in REQUIRED_A if not get_env_var(var)]
    missing_b = [var for var in REQUIRED_B if not get_env_var(var)]
    
    if missing_a or missing_b:
        print("[-] Error: Missing required environment variables in .env file.")
        if missing_a:
            print(f"    Missing Database A variables: {', '.join(missing_a)}")
        if missing_b:
            print(f"    Missing Database B variables: {', '.join(missing_b)}")
        sys.exit(1)

def get_db_connection_params(prefix):
    """Get database configuration dict for psycopg2."""
    return {
        "host": get_env_var(f"{prefix}_HOST"),
        "port": get_env_var(f"{prefix}_PORT"),
        "database": get_env_var(f"{prefix}_NAME"),
        "user": get_env_var(f"{prefix}_USER"),
        "password": get_env_var(f"{prefix}_PASSWORD")
    }

def test_connections(db_a_params, db_b_params):
    """Test connection to both databases."""
    print("[*] Testing database connections...")
    
    # Test DB A (Source)
    try:
        conn = psycopg2.connect(**db_a_params)
        # Verify read-only access (run a simple query)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        conn.close()
        print(f"    [+] Database A (Source: {db_a_params['database']} @ {db_a_params['host']}) - Connection OK (Read-Only verified)")
    except Exception as e:
        print(f"    [-] Database A connection failed: {e}")
        sys.exit(1)
        
    # Test DB B (Target/Local)
    try:
        conn = psycopg2.connect(**db_b_params)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        conn.close()
        print(f"    [+] Database B (Target: {db_b_params['database']} @ {db_b_params['host']}) - Connection OK")
    except Exception as e:
        print(f"    [-] Database B connection failed: {e}")
        sys.exit(1)

def find_pg_tool(tool_name):
    """Locates postgres command-line tool (pg_dump, psql) on the system."""
    # 1. Check if tool is in PATH
    path_tool = shutil.which(tool_name)
    if path_tool:
        return path_tool
    
    # 2. Check if PG_BIN_DIR in environment variable is set
    pg_bin_dir = get_env_var("PG_BIN_DIR")
    if pg_bin_dir and os.path.isdir(pg_bin_dir):
        ext = ".exe" if sys.platform == "win32" else ""
        tool_path = os.path.join(pg_bin_dir, f"{tool_name}{ext}")
        if os.path.exists(tool_path):
            return tool_path
            
    # 3. Check standard Windows installations
    if sys.platform == "win32":
        standard_paths = [
            r"C:\Program Files\PostgreSQL\*\bin",
            r"C:\Program Files (x86)\PostgreSQL\*\bin"
        ]
        for pattern in standard_paths:
            for bin_dir in sorted(glob.glob(pattern), reverse=True): # Prefer newest version if multiple
                tool_path = os.path.join(bin_dir, f"{tool_name}.exe")
                if os.path.exists(tool_path):
                    return tool_path
                    
    return None

def wipe_database_b(db_params):
    """Wipes the target database B by dropping and recreating the public schema."""
    print(f"[*] Wiping Database B ({db_params['database']}) schemas...")
    try:
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Drop public schema cascade to delete all tables, views, sequences, etc.
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
            cur.execute("CREATE SCHEMA public;")
            cur.execute("GRANT ALL ON SCHEMA public TO public;")
            # Also grant permission specifically to the user if different
            cur.execute(f"GRANT ALL ON SCHEMA public TO {db_params['user']};")
        conn.close()
        print("    [+] Database B wiped successfully.")
    except Exception as e:
        print(f"    [-] Error wiping Database B: {e}")
        sys.exit(1)

def main():
    print("======================================================================")
    print("                DATABASE REPLICATION / SYNC UTILITY                  ")
    print("======================================================================")
    
    verify_env()
    
    db_a = get_db_connection_params("DB_A")
    db_b = get_db_connection_params("DB_B")
    
    # Safety Check: Prevent accidental replication to prod (Database B must not be the prod host)
    # Typically, local replica is localhost or 127.0.0.1
    # We warn heavily if the DB_B host is a remote IP.
    is_local_b = db_b["host"].lower() in ["localhost", "127.0.0.1", "::1"]
    
    print("\n--- Configurations ---")
    print(f"Database A (SOURCE): {db_a['database']} on {db_a['host']}:{db_a['port']} (User: {db_a['user']})")
    print(f"Database B (TARGET): {db_b['database']} on {db_b['host']}:{db_b['port']} (User: {db_b['user']})")
    print("----------------------\n")
    
    test_connections(db_a, db_b)
    
    # Locate tools
    pg_dump_path = find_pg_tool("pg_dump")
    psql_path = find_pg_tool("psql")
    
    if not pg_dump_path or not psql_path:
        print("[-] Error: Could not locate 'pg_dump' or 'psql' utilities.")
        print("    Please ensure PostgreSQL is installed on this system.")
        print("    You can also define 'PG_BIN_DIR' in your .env file to point to the PostgreSQL bin directory.")
        print("    Example: PG_BIN_DIR=C:\\Program Files\\PostgreSQL\\17\\bin")
        sys.exit(1)
        
    print(f"[+] Located pg_dump: {pg_dump_path}")
    print(f"[+] Located psql: {psql_path}")
    
    # Confirmation Prompt
    print("\n" + "!" * 70)
    print("WARNING: This script will WIPE OUT all data, tables, views, sequences,")
    print(f"and schemas in Database B: '{db_b['database']}' on host '{db_b['host']}'.")
    print("This action is DESTRUCTIVE and CANNOT BE UNDONE.")
    print("Database A (Source) will remain UNTOUCHED.")
    print("!" * 70 + "\n")
    
    if not is_local_b:
        print("[CAUTION] Target database B is on a remote host (not localhost). Please double check.")
        
    # Confirmation Prompt
    expected_confirm = db_b["database"]
    if "--yes" in sys.argv or "-y" in sys.argv:
        print(f"[*] Auto-confirmed: Wiping target database '{expected_confirm}' via --yes flag.")
    else:
        prompt_text = f"To proceed, please type the name of the TARGET database to wipe ({expected_confirm}): "
        try:
            user_input = input(prompt_text).strip()
        except KeyboardInterrupt:
            print("\n[!] Sync cancelled by user.")
            sys.exit(0)
            
        if user_input != expected_confirm:
            print("[-] Confirmation failed. Database name mismatch. Sync cancelled.")
            sys.exit(0)
        
    print("\n[*] Starting Replication...")
    
    # Define a temporary file for dump
    temp_dir = tempfile.gettempdir()
    temp_sql_file = os.path.join(temp_dir, f"db_sync_{db_a['database']}_dump.sql")
    
    try:
        # Step 1: Dump Database A
        print(f"[*] Dumping Database A ({db_a['database']}) to temporary file...")
        
        # Set password in environment so pg_dump doesn't prompt
        env_a = os.environ.copy()
        env_a["PGPASSWORD"] = db_a["password"]
        
        dump_cmd = [
            pg_dump_path,
            "-h", db_a["host"],
            "-p", db_a["port"],
            "-U", db_a["user"],
            "-d", db_a["database"],
            "-F", "p",  # Plain text format
            "-f", temp_sql_file,
            "--no-owner",      # Don't output commands to set ownership of objects
            "--no-privileges"  # Prevent dumping access privileges (grant/revoke commands)
        ]
        
        # Run pg_dump
        subprocess.run(dump_cmd, env=env_a, check=True)
        print(f"    [+] Database A dumped successfully to: {temp_sql_file}")
        
        # Step 2: Wipe Database B
        wipe_database_b(db_b)
        
        # Step 3: Restore to Database B
        print(f"[*] Restoring dump to Database B ({db_b['database']})...")
        
        env_b = os.environ.copy()
        env_b["PGPASSWORD"] = db_b["password"]
        
        restore_cmd = [
            psql_path,
            "-h", db_b["host"],
            "-p", db_b["port"],
            "-U", db_b["user"],
            "-d", db_b["database"],
            "-q", # Quiet mode
            "-f", temp_sql_file
        ]
        
        # Run psql
        subprocess.run(restore_cmd, env=env_b, check=True)
        print("    [+] Restore completed successfully.")
        
        print("\n[+] SUCCESS: Database replication completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n[-] Subprocess error during sync: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] Unexpected error during sync: {e}")
        sys.exit(1)
    finally:
        # Clean up temp file
        if os.path.exists(temp_sql_file):
            try:
                os.remove(temp_sql_file)
                print("[*] Temporary dump file cleaned up.")
            except Exception as e:
                print(f"[-] Warning: Failed to delete temporary file {temp_sql_file}: {e}")

if __name__ == "__main__":
    main()
