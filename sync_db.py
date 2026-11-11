#!/usr/bin/env python3
"""
Root-level wrapper for scripts/sync_db.py
Allows running: python sync_db.py from the project root.
"""
import os
import sys

scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
sync_script = os.path.join(scripts_dir, "sync_db.py")

if __name__ == "__main__":
    if os.path.exists(sync_script):
        # Execute scripts/sync_db.py with the same arguments and environment
        with open(sync_script, "rb") as f:
            code = compile(f.read(), sync_script, "exec")
        # Ensure scripts directory and root are in sys.path
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        root_dir = os.path.dirname(os.path.abspath(__file__))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        globs = {
            "__file__": sync_script,
            "__name__": "__main__",
            "__doc__": None,
            "__package__": None
        }
        exec(code, globs)
    else:
        print(f"Error: Could not locate {sync_script}")
        sys.exit(1)
