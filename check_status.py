#!/usr/bin/env python3
"""Quick status check for walk-forward validation"""

import os
import json
from datetime import datetime

results_dir = "backtest_results"

files_to_check = {
    "validation_json": "walk_forward_validation.json",
    "summary_csv": "walk_forward_summary.csv",
    "report_md": "walk_forward_report.md"
}

print("\n[STATUS CHECK] Walk-Forward Validation Progress")
print("=" * 70)

for fname, fpath in files_to_check.items():
    full_path = os.path.join(results_dir, fpath)
    if os.path.exists(full_path):
        stat = os.stat(full_path)
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime)
        print(f"  {fname:20s} | Size: {size:10,d} bytes | Modified: {mtime}")
        
        if fpath == "walk_forward_validation.json" and size > 100:
            try:
                with open(full_path) as f:
                    data = json.load(f)
                robust = len(data.get('robust', []))
                overfit = len(data.get('overfit', []))
                weak = len(data.get('weak', []))
                summary_count = len(data.get('summary', []))
                total = robust + overfit + weak
                
                if total > 0:
                    print(f"\n  RESULTS AVAILABLE:")
                    print(f"    ROBUST:  {robust:3d} strategies")
                    print(f"    OVERFIT: {overfit:3d} strategies")
                    print(f"    WEAK:    {weak:3d} strategies")
                    print(f"    TOTAL:   {total:3d} strategies tested")
                else:
                    print(f"\n  Still processing (0 strategies classified yet)...")
            except:
                pass
    else:
        print(f"  {fname:20s} | NOT FOUND")

print("\n" + "=" * 70 + "\n")
