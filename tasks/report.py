"""
tasks/report.py — Sample task: simulate generating a weekly summary report.
"""

import time
import random

print("[INFO] Generating weekly report…", flush=True)
print("[DEBUG] Date range: last 7 days", flush=True)
time.sleep(0.5)

revenue = random.randint(10000, 20000)
new_users = random.randint(200, 500)
churn = round(random.uniform(1.0, 4.5), 1)

print(f"[OK] Revenue: ${revenue:,}", flush=True)
time.sleep(0.4)
print(f"[OK] New users: {new_users}", flush=True)
time.sleep(0.4)

if churn > 3.5:
    print(f"[WARN] Churn rate high: {churn}%", flush=True)
else:
    print(f"[OK] Churn rate: {churn}%", flush=True)

time.sleep(0.5)
print("[INFO] Rendering PDF…", flush=True)
time.sleep(0.8)
print("[OK] report_2025_w18.pdf generated", flush=True)
print("[OK] Report emailed to team@company.com", flush=True)
