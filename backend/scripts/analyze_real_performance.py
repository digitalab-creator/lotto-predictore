"""
🏴‍☠️ CRITICAL ANALYSIS: Real vs Backtest Performance
Analyzes database to determine if predictions have REAL edge or just backtest overfitting
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from db.base import SessionLocal
from models import Prediction, PredictionDetail, Draw
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

def analyze_real_performance():
    """Analyze actual database results to determine real edge"""
    
    db = SessionLocal()
    
    try:
        print("🏴‍☠️ ANALYZING REAL PERFORMANCE FROM DATABASE")
        print("=" * 80)
        print()
        
        # 1. Check if predictions are BACKTEST or REAL
        print("1️⃣ CHECKING PREDICTION TYPE (Backtest vs Real)")
        print("-" * 80)
        
        # Get all predictions with details
        predictions = db.query(Prediction).order_by(desc(Prediction.run_time)).limit(50).all()
        
        backtest_count = 0
        real_count = 0
        unclear_count = 0
        
        for pred in predictions:
            # Check if prediction was made BEFORE the test draws happened
            details = db.query(PredictionDetail).filter(
                PredictionDetail.prediction_id == pred.id
            ).all()
            
            if not details:
                continue
            
            # Check if prediction was made before the draw
            first_detail = details[0]
            draw_date = first_detail.test_draw_date
            prediction_time = pred.run_time
            
            if prediction_time and draw_date:
                if prediction_time.date() < draw_date:
                    # Prediction made before draw = REAL
                    real_count += 1
                else:
                    # Prediction made after draw = BACKTEST
                    backtest_count += 1
            else:
                # Can't determine - likely backtest
                unclear_count += 1
        
        print(f"   Backtest Predictions: {backtest_count}")
        print(f"   Real Predictions: {real_count}")
        print(f"   Unclear: {unclear_count}")
        print()
        
        if backtest_count > real_count * 10:
            print("   ⚠️  WARNING: Most predictions are BACKTESTS, not real!")
            print("   ⚠️  Backtest ROI ≠ Real ROI (backtests can be misleading)")
            print()
        
        # 2. Analyze ALL PredictionDetail records
        print("2️⃣ ANALYZING ALL PREDICTION DETAILS")
        print("-" * 80)
        
        all_details = db.query(PredictionDetail).all()
        total_details = len(all_details)
        
        print(f"   Total Prediction Details: {total_details}")
        
        if total_details == 0:
            print("   ❌ NO DATA FOUND - Cannot analyze performance")
            return
        
        # Calculate statistics
        rois = [detail.roi for detail in all_details if detail.roi is not None]
        prizes = [detail.prize for detail in all_details if detail.prize is not None]
        hits_distribution = defaultdict(int)
        winning_predictions = 0
        
        for detail in all_details:
            hits_distribution[detail.hits] += 1
            if detail.prize and detail.prize > 0:
                winning_predictions += 1
        
        print(f"   Total Predictions Analyzed: {total_details}")
        print(f"   Winning Predictions (prize > 0): {winning_predictions} ({winning_predictions/total_details*100:.2f}%)")
        print()
        
        # ROI Analysis
        if rois:
            avg_roi = statistics.mean(rois)
            median_roi = statistics.median(rois)
            positive_roi_count = sum(1 for r in rois if r > 0)
            negative_roi_count = sum(1 for r in rois if r < 0)
            zero_roi_count = sum(1 for r in rois if r == 0)
            
            print("3️⃣ ROI ANALYSIS")
            print("-" * 80)
            print(f"   Average ROI: {avg_roi:.4f} ({avg_roi*100:.2f}%)")
            print(f"   Median ROI: {median_roi:.4f} ({median_roi*100:.2f}%)")
            print(f"   Positive ROI Predictions: {positive_roi_count} ({positive_roi_count/len(rois)*100:.2f}%)")
            print(f"   Negative ROI Predictions: {negative_roi_count} ({negative_roi_count/len(rois)*100:.2f}%)")
            print(f"   Zero ROI Predictions: {zero_roi_count} ({zero_roi_count/len(rois)*100:.2f}%)")
            print()
            
            # Critical check
            if avg_roi < 0:
                print("   ❌ AVERAGE ROI IS NEGATIVE - System is LOSING money!")
            elif avg_roi < 0.1:
                print("   ⚠️  AVERAGE ROI IS VERY LOW - Not profitable enough")
            elif avg_roi > 0.5:
                print("   ⚠️  AVERAGE ROI IS VERY HIGH - Likely backtest overfitting!")
            else:
                print("   ✅ AVERAGE ROI IS POSITIVE - But verify it's real, not backtest")
            print()
        
        # Hit Distribution
        print("4️⃣ HIT DISTRIBUTION")
        print("-" * 80)
        for hits in sorted(hits_distribution.keys()):
            count = hits_distribution[hits]
            pct = count / total_details * 100
            print(f"   {hits} hits: {count} predictions ({pct:.2f}%)")
        print()
        
        # Prize Analysis
        if prizes:
            total_prize = sum(prizes)
            avg_prize = statistics.mean(prizes)
            max_prize = max(prizes)
            min_prize = min(prizes)
            
            # Calculate total cost (assuming 8 combinations per prediction detail)
            # Actually, each detail is one combo, so cost per detail
            from config import TICKET_COST_PER_TABLE
            total_cost = total_details * TICKET_COST_PER_TABLE
            
            print("5️⃣ PRIZE ANALYSIS")
            print("-" * 80)
            print(f"   Total Prizes Won: ₪{total_prize:,.2f}")
            print(f"   Total Cost: ₪{total_cost:,.2f}")
            print(f"   Net Profit/Loss: ₪{total_prize - total_cost:,.2f}")
            print(f"   Average Prize: ₪{avg_prize:.2f}")
            print(f"   Max Prize: ₪{max_prize:,.2f}")
            print(f"   Min Prize: ₪{min_prize:.2f}")
            print()
            
            overall_roi = (total_prize - total_cost) / total_cost if total_cost > 0 else 0
            print(f"   OVERALL ROI: {overall_roi:.4f} ({overall_roi*100:.2f}%)")
            print()
        
        # 6. Check for REAL predictions (made before draw)
        print("6️⃣ CHECKING FOR REAL PREDICTIONS (Made Before Draw)")
        print("-" * 80)
        
        real_predictions = []
        for detail in all_details[:200]:  # Check first 200
            pred = db.query(Prediction).filter(
                Prediction.id == detail.prediction_id
            ).first()
            
            if pred and pred.run_time and detail.test_draw_date:
                # Check if prediction was made BEFORE draw
                if pred.run_time.date() < detail.test_draw_date:
                    real_predictions.append({
                        'detail': detail,
                        'prediction_time': pred.run_time,
                        'draw_date': detail.test_draw_date,
                        'roi': detail.roi,
                        'prize': detail.prize,
                        'hits': detail.hits
                    })
        
        print(f"   Real Predictions Found: {len(real_predictions)}")
        
        if real_predictions:
            real_rois = [p['roi'] for p in real_predictions if p['roi'] is not None]
            real_prizes = [p['prize'] for p in real_predictions if p['prize'] is not None]
            
            if real_rois:
                real_avg_roi = statistics.mean(real_rois)
                real_median_roi = statistics.median(real_rois)
                real_positive = sum(1 for r in real_rois if r > 0)
                
                print(f"   Real Predictions Average ROI: {real_avg_roi:.4f} ({real_avg_roi*100:.2f}%)")
                print(f"   Real Predictions Median ROI: {real_median_roi:.4f} ({real_median_roi*100:.2f}%)")
                print(f"   Real Predictions with Positive ROI: {real_positive}/{len(real_rois)} ({real_positive/len(real_rois)*100:.2f}%)")
                
                if real_prizes:
                    real_total_prize = sum(real_prizes)
                    real_total_cost = len(real_predictions) * TICKET_COST_PER_TABLE
                    real_overall_roi = (real_total_prize - real_total_cost) / real_total_cost if real_total_cost > 0 else 0
                    print(f"   Real Predictions Overall ROI: {real_overall_roi:.4f} ({real_overall_roi*100:.2f}%)")
                
                print()
                
                if real_avg_roi < 0:
                    print("   ❌ REAL PREDICTIONS ARE LOSING MONEY!")
                elif real_avg_roi < 0.05:
                    print("   ⚠️  REAL PREDICTIONS HAVE LOW ROI")
                elif real_avg_roi > 0.3:
                    print("   ⚠️  REAL PREDICTIONS HAVE VERY HIGH ROI - Verify this is correct")
                else:
                    print("   ✅ REAL PREDICTIONS HAVE POSITIVE ROI")
        else:
            print("   ⚠️  NO REAL PREDICTIONS FOUND - All are backtests!")
            print("   ⚠️  Backtest performance ≠ Real performance!")
        print()
        
        # 7. Compare Backtest vs Real ROI
        if real_predictions and len(real_predictions) > 5:
            print("7️⃣ BACKTEST vs REAL ROI COMPARISON")
            print("-" * 80)
            
            backtest_details = [d for d in all_details if d not in [p['detail'] for p in real_predictions]]
            if backtest_details:
                backtest_rois = [d.roi for d in backtest_details if d.roi is not None]
                if backtest_rois:
                    backtest_avg = statistics.mean(backtest_rois)
                    real_avg = statistics.mean([p['roi'] for p in real_predictions if p['roi'] is not None])
                    
                    print(f"   Backtest Average ROI: {backtest_avg:.4f} ({backtest_avg*100:.2f}%)")
                    print(f"   Real Average ROI: {real_avg:.4f} ({real_avg*100:.2f}%)")
                    print(f"   Difference: {real_avg - backtest_avg:.4f} ({(real_avg - backtest_avg)*100:.2f}%)")
                    print()
                    
                    if backtest_avg > real_avg * 1.5:
                        print("   ⚠️  BACKTEST ROI IS MUCH HIGHER - Classic overfitting sign!")
                        print("   ⚠️  Models perform worse in real use than in backtests")
        
        # 8. FINAL VERDICT
        print("=" * 80)
        print("🏴‍☠️ FINAL VERDICT")
        print("=" * 80)
        
        if total_details == 0:
            print("❌ NO DATA - Cannot determine edge")
        elif backtest_count > real_count * 5:
            print("⚠️  MOSTLY BACKTEST DATA")
            print("   - Backtest ROI can be misleading (overfitting)")
            print("   - Need REAL predictions (made before draw) to verify edge")
            print("   - Current ROI numbers are NOT reliable for real trading")
            print()
            print("   RECOMMENDATION: Generate predictions for FUTURE draws")
            print("   and track their performance before building SaaS")
        elif avg_roi and avg_roi < 0:
            print("❌ NEGATIVE ROI - NO EDGE FOUND")
            print("   - System is losing money on average")
            print("   - Do NOT use for real trading or SaaS")
        elif avg_roi and avg_roi < 0.05:
            print("⚠️  VERY LOW ROI - MINIMAL EDGE")
            print("   - ROI is positive but very small")
            print("   - May not be profitable after fees/taxes")
            print("   - Proceed with caution")
        elif real_predictions and len(real_predictions) > 10:
            real_avg = statistics.mean([p['roi'] for p in real_predictions if p['roi'] is not None])
            if real_avg > 0.1:
                print("✅ REAL EDGE DETECTED")
                print(f"   - Real predictions show {real_avg*100:.2f}% ROI")
                print("   - System may have genuine edge")
                print("   - Can proceed with SaaS or trading")
            elif real_avg > 0:
                print("⚠️  REAL PREDICTIONS SHOW LOW BUT POSITIVE ROI")
                print(f"   - Real performance: {real_avg*100:.2f}% ROI")
                print("   - Proceed with caution - may not be sustainable")
            else:
                print("❌ REAL PREDICTIONS SHOW NEGATIVE ROI")
                print("   - Real performance is worse than backtest")
                print("   - Do NOT proceed with SaaS")
        else:
            print("⚠️  INSUFFICIENT REAL DATA")
            print("   - Need more real predictions to verify edge")
            print("   - Backtest results are not reliable")
            print("   - Do NOT assume backtest ROI = real ROI")
            print()
            print("   RECOMMENDATION:")
            print("   1. Generate predictions for next 10-20 draws")
            print("   2. Track actual results")
            print("   3. Calculate real ROI")
            print("   4. Only then decide on SaaS")
        
        print()
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    analyze_real_performance()

