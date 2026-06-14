#!/usr/bin/env python3
import os
import sys
import argparse
import time
from datetime import datetime, timedelta
import pytz

# Add parent directory to sys.path to enable app and db imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (
    compute_and_cache_behavioral_analytics,
    calculate_village_health_history,
    get_pg_connection
)

# Colors for pretty CLI output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def prefill_village_cache(vid, vname, cur, force_recalc=False):
    KOLKATA = pytz.timezone('Asia/Kolkata')
    today = datetime.now(KOLKATA).date()
    
    # 1. Determine eval_today
    cur.execute("""
        SELECT MAX(payment_date) FROM (
            SELECT payment_date FROM payment WHERE cid IN (SELECT cid FROM customer WHERE vid = %s)
            UNION ALL
            SELECT payment_date FROM closed_cust_payment WHERE cid IN (SELECT cid FROM closed_cust_account WHERE vid = %s)
            UNION ALL
            SELECT payment_date FROM historic_payment_data WHERE cid IN (SELECT cid FROM historic_customer_data WHERE vid = %s)
        ) all_p
    """, (vid, vid, vid))
    latest_payment_row = cur.fetchone()
    latest_payment_in_village = latest_payment_row[0] if latest_payment_row else None
    
    eval_today = today
    if latest_payment_in_village:
        if isinstance(latest_payment_in_village, datetime):
            latest_payment_in_village = latest_payment_in_village.date()
        lag_days = (today - latest_payment_in_village).days
        if lag_days > 7:
            shift_days = min(lag_days, 14)
            eval_today = today - timedelta(days=shift_days)

    # 2. View/subview configurations to cache
    configs = [
        ("active", "active_only"),
        ("active", "active_defaulted"),
        ("complete", "active_only")
    ]
    
    for view, sub_view in configs:
        # Step A: Precompute and cache behavioral analytics (which also writes weekly history)
        compute_and_cache_behavioral_analytics(vid, cur, view, sub_view, today, force_recalc)
        
        # Step B: Generate dates and precompute monthly, yearly, and all ranges
        # Monthly Range
        monthly_dates = [eval_today - timedelta(days=30 * i) for i in range(5, -1, -1)]
        calculate_village_health_history(vid, cur, view, sub_view, monthly_dates, "monthly")
        
        # Yearly Range
        yearly_dates = [eval_today - timedelta(days=30 * i) for i in range(11, -1, -1)]
        calculate_village_health_history(vid, cur, view, sub_view, yearly_dates, "yearly")
        
        # Complete/All Range
        cur.execute("""
            SELECT MIN(start_date) FROM (
                SELECT start_date FROM customer WHERE vid = %s
                UNION ALL
                SELECT start_date FROM closed_cust_account WHERE vid = %s
                UNION ALL
                SELECT start_date FROM historic_customer_data WHERE vid = %s
            ) all_s
        """, (vid, vid, vid))
        min_s_row = cur.fetchone()
        min_start = min_s_row[0] if min_s_row and min_s_row[0] else None
        
        if min_start:
            if isinstance(min_start, datetime):
                min_start = min_start.date()
            total_days = (eval_today - min_start).days
            if total_days <= 0:
                all_dates = [eval_today]
            else:
                if total_days <= 90:
                    step = 7
                elif total_days <= 365:
                    step = 14
                else:
                    step = 30
                
                all_dates = []
                curr = eval_today
                while curr >= min_start:
                    all_dates.append(curr)
                    curr -= timedelta(days=step)
                all_dates.reverse()
                if len(all_dates) > 24:
                    indices = [int(i * (len(all_dates) - 1) / 23) for i in range(24)]
                    all_dates = [all_dates[idx] for idx in indices]
        else:
            all_dates = [eval_today - timedelta(days=30 * i) for i in range(5, -1, -1)]
            
        calculate_village_health_history(vid, cur, view, sub_view, all_dates, "all")

def main():
    parser = argparse.ArgumentParser(description="Prefill/Pre-calculate Village Health and Behavioral Analytics Caches.")
    parser.add_argument("--vid", type=int, help="Limit cache building to a single village ID.")
    parser.add_argument("--force", action="store_true", help="Force recalculate and overwrite existing cache records.")
    args = parser.parse_args()
    
    print(f"{Colors.HEADER}=== Village Health Cache Prefill Tool ==={Colors.ENDC}\n")
    
    conn = get_pg_connection()
    cur = conn.cursor()
    
    # 1. Fetch target villages
    if args.vid:
        cur.execute("SELECT vid, village_name FROM village WHERE vid = %s;", (args.vid,))
        villages = cur.fetchall()
        if not villages:
            print(f"{Colors.FAIL}Error: Village ID {args.vid} not found in database.{Colors.ENDC}")
            sys.exit(1)
    else:
        # Get all villages that have customer accounts (active, closed, or historic)
        cur.execute("""
            SELECT DISTINCT v.vid, v.village_name 
            FROM village v
            WHERE EXISTS (SELECT 1 FROM customer c WHERE c.vid = v.vid)
               OR EXISTS (SELECT 1 FROM closed_cust_account cc WHERE cc.vid = v.vid)
               OR EXISTS (SELECT 1 FROM historic_customer_data hc WHERE hc.vid = v.vid)
            ORDER BY v.village_name;
        """)
        villages = cur.fetchall()
        print(f"Found {len(villages)} villages with customer history to process.")
        
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    # 2. Iterate and pre-populate
    for idx, (vid, vname) in enumerate(villages, 1):
        v_start = time.time()
        print(f"[{idx}/{len(villages)}] Processing {Colors.BOLD}{vname}{Colors.ENDC} (ID: {vid})...", end="", flush=True)
        try:
            prefill_village_cache(vid, vname, cur, force_recalc=args.force)
            conn.commit()  # Progressive commits per village
            success_count += 1
            print(f" {Colors.OKGREEN}Done in {time.time() - v_start:.2f}s{Colors.ENDC}")
        except Exception as ex:
            conn.rollback()
            fail_count += 1
            print(f" {Colors.FAIL}FAILED: {ex}{Colors.ENDC}")
            
    print(f"\n{Colors.HEADER}=== Prefill Execution Summary ==={Colors.ENDC}")
    print(f"  Processed Villages: {len(villages)}")
    print(f"  {Colors.OKGREEN}Successful:         {success_count}{Colors.ENDC}")
    print(f"  {Colors.FAIL}Failed:             {fail_count}{Colors.ENDC}")
    print(f"  Total Duration:     {time.time() - start_time:.2f} seconds.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
