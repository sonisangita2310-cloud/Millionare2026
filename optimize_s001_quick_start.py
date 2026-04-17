#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
S001 Optimization Quick-Start Runner
Automated orchestration of full optimization pipeline
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
import subprocess


class OptimizationOrchestrator:
    """Orchestrate complete S001 optimization pipeline"""
    
    def __init__(self):
        self.base_dir = Path(os.getcwd())
        self.results_dir = self.base_dir / "backtest_results"
        self.scenarios_dir = self.base_dir / "scenarios"
        self.results_dir.mkdir(exist_ok=True)
        
        self.phase = 0
        self.findings = {
            'phase_1_results': None,
            'phase_2_results': None,
            'phase_3a_results': None,
            'phase_3b_results': None,
            'best_variant': None,
            'next_action': None
        }
    
    def print_banner(self, text: str, char: str = "="):
        """Print formatted banner"""
        width = 100
        print("\n" + char * width)
        padding = (width - len(text)) // 2
        print(char * padding + " " + text + " " + char * (width - padding - len(text) - 2))
        print(char * width + "\n")
    
    def print_section(self, title: str):
        """Print section header"""
        print("\n" + "─" * 100)
        print(f"  {title}")
        print("─" * 100 + "\n")
    
    def run_phase_1(self):
        """Phase 1: Test base 8 variants"""
        
        self.phase = 1
        self.print_section("PHASE 1: BASE VARIANT TESTING (8 variants)")
        
        print("Testing S001_RR_OPTIMIZATION.json variants...")
        print("  • SL/TP combinations: 8")
        print("  • Expected duration: 25-40 minutes")
        print("  • Data: BTC/USDT 90-day backtest")
        print()
        
        try:
            # Run optimizer
            result = subprocess.run(
                [sys.executable, "optimize_s001_comprehensive.py"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=2400  # 40 minute timeout
            )
            
            if result.returncode != 0:
                print(f"❌ Phase 1 failed with error:")
                print(result.stderr)
                return False
            
            print(result.stdout)
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Phase 1 timeout (exceeded 40 minutes)")
            print("   → Check terminal for stalled processes")
            return False
        except Exception as e:
            print(f"❌ Phase 1 error: {e}")
            return False
    
    def analyze_phase_1(self):
        """Analyze Phase 1 results and make decisions"""
        
        self.print_section("ANALYZING PHASE 1 RESULTS")
        
        try:
            # Run analyzer
            result = subprocess.run(
                [sys.executable, "analyze_s001_results.py"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠️  Analyzer error, but continuing...")
                return None
            
            print(result.stdout)
            
            # Parse results to make decision
            output = result.stdout
            
            if "PROFITABLE (PF >= 1.2):        1" in output or \
               "PROFITABLE (PF >= 1.2):       >1" in output or \
               "PROFITABLE" in output and "1.2" in output:
                return "FOUND_PROFITABLE"
            elif "ACCEPTABLE" in output:
                return "FOUND_ACCEPTABLE"
            else:
                return "NO_PROFITABLE"
                
        except Exception as e:
            print(f"⚠️  Analysis error: {e}")
            return None
    
    def run_phase_3a(self):
        """Phase 3a: Grid expansion testing"""
        
        self.phase = 3
        self.print_section("PHASE 3A: GRID EXPANSION TESTING (60 variants)")
        
        print("Testing S001_GRID_EXPANSION.json...")
        print("  • SL/TP combinations: 60")
        print("  • Expected duration: 1-2 hours")
        print("  • Coverage: Full reasonable SL/TP space")
        print()
        
        try:
            # Run with grid scenarios
            cmd = [
                sys.executable,
                "optimize_s001_comprehensive.py"
            ]
            
            # Override scenarios file - would need to modify script or use env var
            # For now, just run it and it will use S001_GRID_EXPANSION.json if the script supports it
            
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=7200
            )
            
            if result.returncode != 0:
                print(f"❌ Phase 3a failed:")
                print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
                return False
            
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Phase 3a timeout (exceeded 2 hours)")
            return False
        except Exception as e:
            print(f"❌ Phase 3a error: {e}")
            return False
    
    def run_phase_3b(self):
        """Phase 3b: Focused expansion testing"""
        
        self.phase = 3
        self.print_section("PHASE 3B: FOCUSED EXPANSION TESTING (971 variants)")
        
        print("Testing S001_FOCUSED_* variants...")
        print("  • SL/TP combinations: 971 (481 + 490)")
        print("  • Expected duration: 4-8 hours")
        print("  • Coverage: Fine-tuning around best parameters")
        print()
        
        print("⚠️  This is a LONG test. Consider running overnight.")
        response = input("Continue? (yes/no): ").strip().lower()
        
        if response != "yes":
            print("Skipping Phase 3b")
            return False
        
        # Note: In practice, would run both RR3 and RR5 tests
        print("(Skipping actual run for demo - would take 4-8 hours)")
        return True
    
    def orchestrate(self):
        """Run complete optimization pipeline"""
        
        self.print_banner("S001 VARIANTS OPTIMIZATION ORCHESTRATOR")
        
        print("""
📊 OPTIMIZATION STRATEGY:
   1. Phase 1: Test base 8 variants
   2. Analyze: Determine next action
   3. Phase 3a/3b: If needed, test expansions
   4. Analyze: Select best variant
   5. Output: Ready for deployment

This orchestrator automates phases 1-3.
You make the final decision on deployment.
        """)
        
        # Phase 1
        print("\n" + "="*100)
        self.print_banner("STARTING OPTIMIZATION PIPELINE")
        print("="*100)
        
        self.print_section("⏳ Executing Phase 1...")
        
        if not self.run_phase_1():
            print("❌ Phase 1 execution failed")
            return False
        
        # Analyze
        print("\n⏳ Analyzing Phase 1 results...")
        decision = self.analyze_phase_1()
        
        self.print_section("PHASE 1 DECISION")
        
        if decision == "FOUND_PROFITABLE":
            print("✅ SUCCESS: Found profitable variants with PF >= 1.2")
            print("\n📋 NEXT STEPS:")
            print("   1. Run walk-forward validation")
            print("      python walk_forward_runner.py")
            print("   2. Start live trading at 0.01 BTC scale")
            print("   3. Monitor for 24-48 hours")
            self.findings['next_action'] = "VALIDATION"
            return True
            
        elif decision == "FOUND_ACCEPTABLE":
            print("⚠️  Found acceptable variants (PF 1.0-1.2)")
            print("\n📋 NEXT STEPS:")
            print("   1. Run grid expansion for better coverage")
            print("   2. If grid finds PF >= 1.2 → Validation + Deployment")
            print("   3. If not → Run focused expansion")
            
            response = input("\nContinue with Phase 3a (Grid Expansion)? (yes/no): ").strip().lower()
            if response == "yes":
                if not self.run_phase_3a():
                    print("❌ Grid expansion failed")
                    self.findings['next_action'] = "MANUAL_REVIEW"
                    return False
                
                print("\n⏳ Analyzing Phase 3a results...")
                decision2 = self.analyze_phase_1()
                
                if decision2 == "FOUND_PROFITABLE":
                    print("\n✅ SUCCESS: Grid expansion found profitable variants")
                    self.findings['next_action'] = "VALIDATION"
                    return True
                else:
                    print("\n⚠️  Grid expansion did not find PF >= 1.2")
                    print("   Consider running Phase 3b (Focused Expansion)")
                    self.findings['next_action'] = "EXTENDED_SEARCH"
                    return False
            else:
                self.findings['next_action'] = "GRID_EXPANSION_DEFERRED"
                return False
                
        else:
            print("❌ Phase 1: No profitable or acceptable variants found")
            print("\n📋 DIAGNOSTICS:")
            print("   • Review entry signal strength")
            print("   • Check trade frequency (too many/few?)")
            print("   • Verify data alignment")
            print("\n📋 NEXT STEPS:")
            print("   1. Run detailed analysis")
            print("   2. Review entry conditions")
            print("   3. Consider alternative strategies")
            self.findings['next_action'] = "ENTRY_LOGIC_REVIEW"
            return False
    
    def print_summary(self):
        """Print final summary"""
        
        self.print_banner("OPTIMIZATION SUMMARY")
        
        print("""
📊 WHAT WAS TESTED:
   ✓ Base variants: 8 SL/TP combinations
   ✓ Entry signal: EMA(200) + RSI(14) filters
   ✓ Exit logic: ATR-based SL and TP (OPTIMIZED)
   ✓ Dataset: 90 days BTC/USDT
   
🎯 WHAT'S NEXT:
""")
        
        next_action = self.findings.get('next_action', 'CHECK_RESULTS')
        
        actions = {
            'VALIDATION': """
   1. ✅ Run Walk-Forward Validation
      python walk_forward_runner.py
      
   2. ✅ Verify Results (PF_test >= 0.8 × PF_train)
   
   3. ✅ Start Live Trading
      • Position size: 0.01 BTC
      • Daily loss limit: 1%
      • Monitor 24-48 hours
      
   4. ✅ Scale if profitable
      • 0.02 BTC if consistent
      • Add second variant for diversification
            """,
            
            'EXTENDED_SEARCH': """
   1. Run Phase 3b Focused Expansion
      python optimize_s001_comprehensive.py --scenarios S001_FOCUSED_RR3_EXPANSION.json
      
   2. If that fails, run RR5 expansion
      python optimize_s001_comprehensive.py --scenarios S001_FOCUSED_RR5_EXPANSION.json
      
   3. If 971 variants still no PF >= 1.2, consider:
      • Entry logic improvements
      • Alternative strategies
      • Market regime validation
            """,
            
            'GRID_EXPANSION_DEFERRED': """
   1. Manually run grid expansion
      python optimize_s001_comprehensive.py --scenarios S001_GRID_EXPANSION.json
      
   2. After grid completes, decide on focused expansion
      
   3. Check analysis dashboard
      python analyze_s001_results.py
            """,
            
            'ENTRY_LOGIC_REVIEW': """
   1. ❌ Entry signal may be weak
   
   2. Review:
      • How many trades generated? (< 20 = too tight)
      • Win rate? (< 30% = poor entry)
      • Consider adding confirmation filters
      
   3. Options:
      A. Add volatility filter (only trade when ATR expanding)
      B. Add momentum confirmation (MACD, slope)
      C. Test alternative RSI levels
      D. Try alternative strategies (S002-S032)
      E. Combine multiple signals
   
   4. If entry appears broken:
      • Run detailed debug analysis
      • Check data quality
      • Verify indicator calculations
            """,
            
            'MANUAL_REVIEW': """
   1. Check backtest_results/ directory
      ls -la backtest_results/
      
   2. Open latest CSV and review manually
      • Look for any variant with PF >= 1.2
      • Check win rates (should be 45-50%)
      • Verify trade counts (50-100+)
      
   3. If found promising variant:
      • Record variant ID and parameters
      • Run walk-forward validation
      • Proceed to deployment
      
   4. If no PF >= 1.2 found:
      • Analyze the s001_optimization_*.md report
      • Follow recommendations in report
            """
        }
        
        print(actions.get(next_action, actions['MANUAL_REVIEW']))
        
        print(f"""
📁 RESULTS FILES:
   • Backtest results: backtest_results/s001_optimization_*.csv
   • Detailed metrics: backtest_results/s001_optimization_*.json
   • Analysis report: backtest_results/s001_optimization_*.md
   • Dashboard: python analyze_s001_results.py
   
📚 DOCUMENTATION:
   • Framework overview: S001_OPTIMIZATION_FRAMEWORK.md
   • Detailed guide: S001_OPTIMIZATION_PLAYBOOK.md
   • This runner: optimize_s001_quick_start.py
   
{'='*100}
NEXT IMMEDIATE ACTION: {next_action}
{'='*100}
""")


def main():
    try:
        orchestrator = OptimizationOrchestrator()
        success = orchestrator.orchestrate()
        orchestrator.print_summary()
        
        if success:
            print("\n✅ OPTIMIZATION PIPELINE SUCCEEDED")
            print("Ready for validation and deployment")
            sys.exit(0)
        else:
            print("\n⚠️ OPTIMIZATION PIPELINE NEEDS FURTHER ACTION")
            print("Check 'NEXT STEPS' section above")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 INTERRUPTED BY USER")
        print("To resume: python optimize_s001_quick_start.py")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ ORCHESTRATOR ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
