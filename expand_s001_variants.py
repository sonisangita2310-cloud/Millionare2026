#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
S001 Variants Expansion Generator
Create extended SL/TP combinations for broader optimization
"""

import json
from typing import List, Dict, Tuple


class VariantExpander:
    """Generates extended variants by testing broader SL/TP ranges"""
    
    @staticmethod
    def generate_grid_variants(
        sl_range: Tuple[float, float, float] = (0.5, 1.5, 0.1),
        tp_range: Tuple[float, float, float] = (2.0, 5.0, 0.5),
        use_pairs: bool = True
    ) -> List[Dict]:
        """
        Generate variant grid
        
        Args:
            sl_range: (min, max, step) for SL multiplier
            tp_range: (min, max, step) for TP multiplier
            use_pairs: if True, only create complementary pairs
        """
        
        variants = []
        variant_count = 0
        
        sl_min, sl_max, sl_step = sl_range
        tp_min, tp_max, tp_step = tp_range
        
        # Generate all combinations
        sl_values = []
        sl = sl_min
        while sl <= sl_max + 0.001:  # Float comparison buffer
            sl_values.append(round(sl, 2))
            sl += sl_step
        
        tp_values = []
        tp = tp_min
        while tp <= tp_max + 0.001:
            tp_values.append(round(tp, 2))
            tp += tp_step
        
        for sl_mult in sl_values:
            for tp_mult in tp_values:
                # Filter: avoid extreme ratios
                rr = tp_mult / sl_mult
                
                # Skip if R:R < 1.5 or > 5.0 (unrealistic)
                if rr < 1.5 or rr > 5.0:
                    continue
                
                # Skip tight SL with high TP (too unrealistic)
                if sl_mult < 0.7 and tp_mult > 4.5:
                    continue
                
                variant_count += 1
                variant_id = f"S001_GRID_{variant_count:02d}"
                
                variants.append({
                    "id": variant_id,
                    "name": f"S001 - SL={sl_mult}x ATR, TP={tp_mult}x ATR (R:R={rr:.2f})",
                    "category": "A",
                    "type": "LONG",
                    "edge_type": "trend_continuation",
                    "timeframe_primary": "3m",
                    "timeframes": ["3m", "1h"],
                    "sl_multiplier": sl_mult,
                    "tp_multiplier": tp_mult,
                    "entry": {
                        "conditions": [
                            {
                                "id": "e1",
                                "indicator": "price",
                                "comparison": ">",
                                "reference": "EMA_200_3m",
                                "buffer_pct": 0.001,
                                "logic": "AND"
                            },
                            {
                                "id": "e2",
                                "indicator": "RSI_14",
                                "timeframe": "1h",
                                "comparison": ">",
                                "value": 50
                            },
                            {
                                "id": "e3",
                                "indicator": "RSI_14",
                                "timeframe": "1h",
                                "comparison": "<",
                                "value": 70
                            },
                            {
                                "id": "e4",
                                "indicator": "price",
                                "comparison": ">",
                                "reference": "EMA_200_1h",
                                "buffer_pct": 0.0
                            }
                        ],
                        "confirmation": "All conditions must be true"
                    },
                    "risk_parameters": {
                        "risk_per_trade_pct": 1.5,
                        "expected_win_rate": 0.48,
                        "expected_rr": rr
                    }
                })
        
        return variants
    
    @staticmethod
    def generate_focused_variants(
        base_sl: float = 1.0,
        base_tp: float = 3.0,
        variation_pct: float = 20
    ) -> List[Dict]:
        """
        Generate focused variants around a base configuration
        
        Args:
            base_sl: Base SL multiplier
            base_tp: Base TP multiplier
            variation_pct: Percentage variation to test (+/- this much)
        """
        
        variants = []
        variant_count = 0
        
        # Calculate variation range
        sl_min = base_sl * (1 - variation_pct/100)
        sl_max = base_sl * (1 + variation_pct/100)
        tp_min = base_tp * (1 - variation_pct/100)
        tp_max = base_tp * (1 + variation_pct/100)
        
        # Generate finer grid
        step = 0.05
        
        sl_vals = []
        sl = round(sl_min, 2)
        while sl <= round(sl_max, 2) + 0.001:
            sl_vals.append(round(sl, 2))
            sl = round(sl + step, 2)
        
        tp_vals = []
        tp = round(tp_min, 2)
        while tp <= round(tp_max, 2) + 0.001:
            tp_vals.append(round(tp, 2))
            tp = round(tp + step, 2)
        
        for sl_mult in sl_vals:
            for tp_mult in tp_vals:
                if tp_mult <= sl_mult:
                    continue
                
                variant_count += 1
                variant_id = f"S001_FOCUSED_{variant_count:02d}"
                rr = round(tp_mult / sl_mult, 2)
                
                variants.append({
                    "id": variant_id,
                    "name": f"S001 - SL={sl_mult}x ATR, TP={tp_mult}x ATR (R:R={rr})",
                    "category": "A",
                    "type": "LONG",
                    "edge_type": "trend_continuation",
                    "timeframe_primary": "3m",
                    "timeframes": ["3m", "1h"],
                    "sl_multiplier": sl_mult,
                    "tp_multiplier": tp_mult,
                    "entry": {
                        "conditions": [
                            {
                                "id": "e1",
                                "indicator": "price",
                                "comparison": ">",
                                "reference": "EMA_200_3m",
                                "buffer_pct": 0.001,
                                "logic": "AND"
                            },
                            {
                                "id": "e2",
                                "indicator": "RSI_14",
                                "timeframe": "1h",
                                "comparison": ">",
                                "value": 50
                            },
                            {
                                "id": "e3",
                                "indicator": "RSI_14",
                                "timeframe": "1h",
                                "comparison": "<",
                                "value": 70
                            },
                            {
                                "id": "e4",
                                "indicator": "price",
                                "comparison": ">",
                                "reference": "EMA_200_1h",
                                "buffer_pct": 0.0
                            }
                        ],
                        "confirmation": "All conditions must be true"
                    },
                    "risk_parameters": {
                        "risk_per_trade_pct": 1.5,
                        "expected_win_rate": 0.48,
                        "expected_rr": rr
                    }
                })
        
        return variants


def main():
    print("\n" + "="*100)
    print(" "*25 + "S001 VARIANTS EXPANSION GENERATOR")
    print("="*100)
    
    # Load existing variants from S001_RR_OPTIMIZATION.json
    with open("scenarios/S001_RR_OPTIMIZATION.json", 'r') as f:
        base_config = json.load(f)
    
    base_scenarios = base_config['scenarios']
    print(f"\n📊 Base Configuration:")
    print(f"   • Existing S001 variants: {len(base_scenarios)}")
    print(f"   • Current SL range: 0.8x - 1.2x ATR")
    print(f"   • Current TP range: 3.0x - 4.0x ATR")
    
    # Generate expanded variants
    print(f"\n⚙️  Generating variant expansion sets...\n")
    
    # Set 1: Broad grid covering all reasonable combinations
    print("[1/3] Grid Expansion (Narrow SL, High TP options)")
    grid_variants = VariantExpander.generate_grid_variants(
        sl_range=(0.5, 1.5, 0.1),
        tp_range=(2.0, 5.0, 0.5)
    )
    print(f"      Generated {len(grid_variants)} grid variants")
    
    # Set 2: Focused variants around best initial configuration (assumed SL=1.0, TP=3.0)
    print("\n[2/3] Focused Expansion (Tight tuning around base)")
    focused_rr1 = VariantExpander.generate_focused_variants(
        base_sl=1.0,
        base_tp=3.0,
        variation_pct=30
    )
    print(f"      Generated {len(focused_rr1)} focused variants (base R:R=3.0)")
    
    # Set 3: Focused variants around higher R:R
    print("\n[3/3] Focused Expansion (High R:R options)")
    focused_rr2 = VariantExpander.generate_focused_variants(
        base_sl=0.8,
        base_tp=4.0,
        variation_pct=30
    )
    print(f"      Generated {len(focused_rr2)} focused variants (base R:R=5.0)")
    
    total_new = len(grid_variants) + len(focused_rr1) + len(focused_rr2)
    print(f"\n📈 Total new variants generated: {total_new}")
    
    # Save each set
    print(f"\n💾 Saving variant sets...\n")
    
    # Grid set
    grid_config = {
        "metadata": {
            "total_scenarios": len(grid_variants),
            "version": "3.0",
            "phase": "S001 Grid Expansion",
            "date": "2026-04-17",
            "note": "Broad coverage of SL/TP combinations"
        },
        "scenarios": grid_variants
    }
    
    with open("scenarios/S001_GRID_EXPANSION.json", 'w') as f:
        json.dump(grid_config, f, indent=2)
    print(f"   ✓ Grid variants: scenarios/S001_GRID_EXPANSION.json ({len(grid_variants)} variants)")
    
    # Focused RR=3.0
    focused1_config = {
        "metadata": {
            "total_scenarios": len(focused_rr1),
            "version": "3.0",
            "phase": "S001 Focused RR=3.0 Expansion",
            "date": "2026-04-17",
            "note": "Tight tuning around SL=1.0 TP=3.0"
        },
        "scenarios": focused_rr1
    }
    
    with open("scenarios/S001_FOCUSED_RR3_EXPANSION.json", 'w') as f:
        json.dump(focused1_config, f, indent=2)
    print(f"   ✓ Focused RR=3.0: scenarios/S001_FOCUSED_RR3_EXPANSION.json ({len(focused_rr1)} variants)")
    
    # Focused RR=5.0
    focused2_config = {
        "metadata": {
            "total_scenarios": len(focused_rr2),
            "version": "3.0",
            "phase": "S001 Focused RR=5.0 Expansion",
            "date": "2026-04-17",
            "note": "Tight tuning around SL=0.8 TP=4.0"
        },
        "scenarios": focused_rr2
    }
    
    with open("scenarios/S001_FOCUSED_RR5_EXPANSION.json", 'w') as f:
        json.dump(focused2_config, f, indent=2)
    print(f"   ✓ Focused RR=5.0: scenarios/S001_FOCUSED_RR5_EXPANSION.json ({len(focused_rr2)} variants)")
    
    print(f"\n" + "="*100)
    print(" "*30 + "EXPANSION COMPLETE")
    print("="*100)
    
    print(f"\n📋 Usage Guide:")
    print(f"   1. Start with base 8 variants: scenarios/S001_RR_OPTIMIZATION.json")
    print(f"   2. If no profitable (PF >= 1.2) found, test grid expansion")
    print(f"   3. Refine with focused expansions around best performer")
    print(f"   4. Each file ready to use with optimize_s001_comprehensive.py\n")
    
    print(f"🎯 Summary:")
    print(f"   • Base variants: {len(base_scenarios)}")
    print(f"   • Grid expansion: {len(grid_variants)}")
    print(f"   • Focused expansions: {len(focused_rr1) + len(focused_rr2)}")
    print(f"   • Total available: {len(base_scenarios) + total_new}\n")


if __name__ == "__main__":
    main()
