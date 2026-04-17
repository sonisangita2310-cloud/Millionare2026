#!/usr/bin/env python3
"""
Real-time progress monitor for validator
Tracks: current strategy, time per strategy, CPU usage
"""
import subprocess
import time
import psutil
import re
from datetime import datetime

print("PROGRESS MONITOR - Real-time tracking")
print("=" * 60)

start_time = time.time()
last_strategy_idx = 0
last_strategy_time = start_time
strategy_times = []

try:
    while True:
        # Get last 5 lines of terminal output
        result = subprocess.run(
            ['powershell', '-Command', 'Get-Content wf_validated_optimized.log -Tail 5 -ErrorAction SilentlyContinue'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout
        
        # Parse current strategy index
        match = re.search(r'\[(\d+)/32\]', output)
        if match:
            idx = int(match.group(1))
            elapsed = time.time() - start_time
            
            # If strategy advanced
            if idx > last_strategy_idx:
                if last_strategy_idx > 0:
                    strat_time = elapsed - sum(strategy_times)
                    strategy_times.append(strat_time)
                    avg_time = sum(strategy_times) / len(strategy_times)
                    remaining = (32 - idx) * avg_time
                    
                    print(f"[{idx}/32] ADVANCED | Time: {strat_time:.1f}s | Avg: {avg_time:.1f}s/strat | Est. remaining: {remaining/60:.1f}min")
                else:
                    print(f"[{idx}/32] STARTED")
                
                last_strategy_idx = idx
        
        # Get CPU
        try:
            procs = [p for p in psutil.process_iter(['pid', 'name', 'cpu_num']) if 'python' in p.info['name']]
            if procs:
                total_cpu = sum(p.cpu_num() for p in procs)
                print(f"    CPU cores active: {total_cpu}, Elapsed: {(time.time()-start_time)/60:.1f}min")
        except:
            pass
        
        time.sleep(5)

except KeyboardInterrupt:
    print("\nMonitor stopped")
except Exception as e:
    print(f"Monitor error: {e}")
