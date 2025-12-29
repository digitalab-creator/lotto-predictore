# 1. Ensemble Prediction System

**Priority: MUST HAVE**  
**Impact: High**  
**Effort: Medium**

## Problem Statement

Currently, the system selects a single "best" algorithm pair based on ROI from grid search. This approach has several limitations:

1. **Single Point of Failure**: If the selected algorithm underperforms, the entire week's predictions are affected
2. **Missed Opportunities**: Other top-performing algorithms might have complementary strengths
3. **Overfitting Risk**: The algorithm that performs best on historical data might not generalize to future draws
4. **No Diversification**: All predictions come from one algorithm, increasing risk

## Solution Overview

Create an ensemble system that combines the top 3-5 algorithm pairs using weighted voting based on historical performance. This will:

- Reduce risk through diversification
- Capture complementary patterns from different algorithms
- Improve consistency across different draw types
- Automatically adapt to changing patterns

## Implementation Details

### 1.1 Ensemble Service Architecture

**File**: `backend/services/core/ensemble_service.py`

```python
class EnsembleService:
    """
    Combines multiple algorithm pairs to generate more robust predictions.
    Uses weighted voting based on historical performance.
    """
    
    def __init__(self, db: Session, performance_analyzer: PerformanceAnalyzer):
        self.db = db
        self.performance_analyzer = performance_analyzer
        self.simulation_engine = SimulationEngine(db)
    
    def select_top_algorithms(
        self, 
        draws: List[Draw], 
        top_k: int = 5,
        min_historical_roi: float = -0.5
    ) -> List[Dict[str, Any]]:
        """
        Select top K algorithm pairs based on:
        1. Recent ROI performance (last 4 weeks)
        2. Historical consistency (Sharpe-like ratio)
        3. Win rate (percentage of profitable draws)
        
        Returns list of algorithm pairs with weights
        """
        # Get historical performance for all algorithm pairs
        # Calculate composite score
        # Return top K with weights
        pass
    
    def generate_ensemble_combinations(
        self,
        draws: List[Draw],
        algorithm_pairs: List[Dict[str, Any]],
        top_n: int = 3,
        num_to_recommend: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Generate combinations from each algorithm pair, then combine using:
        1. Frequency-based selection (most common numbers across algorithms)
        2. Weighted selection (weight by algorithm performance)
        3. Diversity enforcement (ensure combinations are different)
        """
        # Generate from each algorithm
        # Combine using weighted frequency
        # Select diverse final combinations
        pass
    
    def calculate_algorithm_weights(
        self,
        algorithm_pairs: List[Dict[str, Any]],
        lookback_weeks: int = 8
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate weights for each algorithm pair based on:
        - Recent ROI (40% weight)
        - Historical consistency (30% weight)
        - Win rate (20% weight)
        - Strong number accuracy (10% weight)
        """
        pass
```

### 1.2 Combination Strategy

**Frequency-Based Selection**:
1. Generate combinations from each algorithm (weighted by algorithm performance)
2. Count frequency of each number across all combinations
3. Select top numbers by weighted frequency
4. Generate final combinations ensuring diversity

**Weighted Voting**:
- Each algorithm's combinations are weighted by its historical performance
- Numbers appearing in higher-performing algorithms get more weight
- Final selection balances frequency and algorithm quality

**Diversity Enforcement**:
- Ensure final combinations are sufficiently different (minimum Hamming distance)
- Avoid duplicate or near-duplicate combinations
- Balance between popular numbers and algorithm-specific picks

### 1.3 Integration Points

**Update Weekly Generation**:
- Modify `standard_combinations.py` to support ensemble mode
- Add parameter `use_ensemble: bool = True` (default True)
- Fallback to single best algorithm if ensemble fails

**Grid Search Integration**:
- Grid search should evaluate ensemble combinations
- Test different ensemble sizes (3, 4, 5 algorithms)
- Optimize ensemble weights

### 1.4 Database Changes

**New Table**: `ensemble_configurations`
```sql
CREATE TABLE ensemble_configurations (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    algorithm_pairs JSONB NOT NULL,  -- List of {main_algo, strong_algo, weight}
    ensemble_size INTEGER NOT NULL,
    performance_metrics JSONB,  -- {roi, sharpe, win_rate, etc}
    is_active BOOLEAN DEFAULT TRUE
);
```

**Update Prediction Model**:
- Add `ensemble_config_id` to `predictions` table
- Track which ensemble configuration was used

### 1.5 API Endpoints

**New Endpoint**: `/api/cron/generate-weekly-combinations-ensemble`
- Similar to standard endpoint but uses ensemble
- Returns ensemble configuration used
- Includes performance metrics for each algorithm in ensemble

**Update Existing Endpoint**:
- Add `?ensemble=true` parameter to standard endpoint
- Default to ensemble mode for better results

### 1.6 Testing Strategy

1. **Historical Backtesting**:
   - Test ensemble vs single algorithm on last 12 weeks
   - Measure ROI improvement
   - Measure consistency (variance reduction)

2. **A/B Testing**:
   - Run both ensemble and single algorithm
   - Compare results over 4-8 weeks
   - Track which performs better

3. **Performance Metrics**:
   - Track ensemble ROI vs single algorithm ROI
   - Measure hit rate improvement
   - Monitor consistency metrics

### 1.7 Expected Outcomes

- **ROI Improvement**: 10-20% increase through diversification
- **Consistency**: 30-50% reduction in variance
- **Hit Rate**: 5-10% improvement in average hits per draw
- **Risk Reduction**: Lower maximum drawdown

### 1.8 Implementation Steps

1. Create `EnsembleService` class with core methods
2. Implement algorithm selection logic
3. Implement combination generation and merging
4. Add database models for ensemble tracking
5. Create ensemble endpoint
6. Update standard endpoint to support ensemble
7. Add comprehensive logging
8. Test with historical data
9. Deploy and monitor

### 1.9 Dependencies

- Performance Analyzer (for historical data)
- Risk Metrics (for consistency scoring)
- Database models for tracking

### 1.10 Rollout Plan

1. **Phase 1**: Implement and test with historical data (1 week)
2. **Phase 2**: Run in parallel with standard method (2 weeks)
3. **Phase 3**: Make ensemble default if performance is better (ongoing)
4. **Phase 4**: Optimize ensemble size and weights based on results


