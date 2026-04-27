"""
tasks/backup.py — Sample task: simulate a database backup.
"""

import time
import random

TABLES = ["users", "orders", "products", "sessions", "audit_log"]

print("[INFO] Connecting to database…", flush=True)
time.sleep(0.6)
print("[OK] Connected to postgres://localhost:5432/mydb", flush=True)

total_rows = 0
for table in TABLES:
    rows = random.randint(100, 20000)
    print(f"[INFO] Backing up {table}…", flush=True)
    time.sleep(0.5)
    if rows == 0:
        print(f"[WARN] {table} is empty — skipping", flush=True)
    else:
        total_rows += rows
        print(f"[OK] {table}: {rows:,} rows exported", flush=True)

print(f"[DEBUG] Total rows: {total_rows:,}", flush=True)
print("[INFO] Compressing backup…", flush=True)
time.sleep(0.8)

size_mb = round(total_rows * 0.0012, 1)
print(f"[OK] Compressed to backup.tar.gz ({size_mb} MB)", flush=True)
print("[OK] Backup complete", flush=True)
