#!/usr/bin/env python3
"""
One-time DB reset script for Supabase/Postgres.

Usage:
  # interactive (will prompt for confirmation)
  python reset_db.py

  # non-interactive with backup
  python reset_db.py --yes --backup

This script reads `supabase_schema.sql` from the backend folder and executes
its statements against the database pointed to by the `DATABASE_URL` env var.
It can optionally run `pg_dump` to create a backup (if `pg_dump` is available).
Be careful: this is destructive.
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

def run_backup(database_url: str) -> str | None:
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"supabase_backup_{now}.dump"
    try:
        print(f"Running pg_dump to create backup: {filename} ...")
        subprocess.run(["pg_dump", database_url, "-Fc", "-f", filename], check=True)
        print(f"Backup written to {filename}")
        return filename
    except FileNotFoundError:
        print("pg_dump not found on PATH — skipping backup. Install Postgres client to enable backups.")
        return None
    except subprocess.CalledProcessError as e:
        print("pg_dump failed:", e)
        return None


def execute_schema(database_url: str, sql_path: str) -> None:
    import psycopg2

    print(f"Connecting to database and executing schema from {sql_path} ...")
    conn = psycopg2.connect(dsn=database_url)
    conn.autocommit = True
    cur = conn.cursor()

    sql = open(sql_path, "r", encoding="utf-8").read()

    # Naive split on semicolon. The provided schema is simple DDL; this works for that.
    parts = [p.strip() for p in sql.split(";") if p.strip()]
    try:
        for stmt in parts:
            cur.execute(stmt + ";")
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="One-time reset of Supabase schema from SQL file")
    parser.add_argument("--sql", default=os.path.join(os.path.dirname(__file__), "supabase_schema.sql"), help="Path to SQL schema file")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--backup", action="store_true", help="Attempt to run pg_dump to create a backup before resetting")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable is not set. Aborting.")
        sys.exit(1)

    print("WARNING: This will DROP and recreate tables in the database:")
    print(f"  {database_url}")
    if not args.yes:
        print("Type 'RESET' (uppercase) to proceed, or Ctrl-C to abort.")
        resp = input("Proceed? ")
        if resp.strip() != "RESET":
            print("Aborted by user.")
            sys.exit(0)

    if args.backup:
        run_backup(database_url)

    if not os.path.exists(args.sql):
        print(f"SQL schema file not found: {args.sql}")
        sys.exit(1)

    try:
        execute_schema(database_url, args.sql)
        print("Schema executed successfully.")
    except Exception as e:
        print("Error while executing schema:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
