# 3. Risk-Adjusted Metrics

**Priority: MUST HAVE**  
**Impact: High**  
**Effort: Low-Medium**

## Problem Statement

Currently, the system optimizes only on ROI, which has significant limitations:

1. **No Risk Consideration**: High ROI might come with high variance (unstable)
2. **No Consistency Measure**: Can't distinguish between consistent performers and volatile ones
3. **No Win Rate Tracking**: An algorithm might have high ROI but low win rate (few big wins vs many small losses)
4. **No Drawdown Protection**: Doesn't consider worst-case scenarios

## Solution Overview

Implement risk-adjusted metrics similar to financial portfolio management:
- Sharpe-like ratio: Risk-adjusted return
- Win rate: Percentage of profitable draws
- Consistency score: Stability of returns
- Maximum drawdown: Worst consecutive performance
- Sortino ratio: Downside risk adjustment

## Implementation Details

### 3.1 Risk Metrics Service

**File**: `backend/services/core/risk_metrics.py`

```python
class RiskMetricsCalculator:
    """
    Calculate risk-adjusted metrics for algorithm performance evaluation.
    Similar to financial portfolio metrics (Sharpe, Sortino, etc.)
    """
    
    def calculate_sharpe_like_ratio(
        self,
        roi_values: List[float],
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Sharpe-like ratio: (Mean ROI - Risk Free Rate) / StdDev(ROI)
        Higher is better - indicates better risk-adjusted returns
        """
        if not roi_values or len(roi_values) < 2:
            return 0.0
        
        mean_roi = np.mean(roi_values)
        std_roi = np.std(roi_values)
        
        if std_roi == 0:
            return float('inf') if mean_roi > 0 else 0.0
        
        return (mean_roi - risk_free_rate) / std_roi
    
    def calculate_sortino_ratio(
        self,
        roi_values: List[float],
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Sortino ratio: (Mean ROI - Risk Free Rate) / Downside Deviation
        Only penalizes negative returns (downside risk)
        """
        if not roi_values or len(roi_values) < 2:
            return 0.0
        
        mean_roi = np.mean(roi_values)
        negative_returns = [r for r in roi_values if r < 0]
        
        if not negative_returns:
            return float('inf') if mean_roi > 0 else 0.0
        
        downside_dev = np.std(negative_returns)
        
        if downside_dev == 0:
            return float('inf') if mean_roi > 0 else 0.0
        
        return (mean_roi - risk_free_rate) / downside_dev
    
    def calculate_win_rate(
        self,
        roi_values: List[float]
    ) -> float:
        """
        Percentage of draws with positive ROI
        """
        if not roi_values:
            return 0.0
        
        wins = sum(1 for r in roi_values if r > 0)
        return wins / len(roi_values)
    
    def calculate_max_drawdown(
        self,
        roi_values: List[float]
    ) -> float:
        """
        Maximum consecutive negative ROI period
        Returns the worst cumulative loss
        """
        if not roi_values:
            return 0.0
        
        max_dd = 0.0
        cumulative = 0.0
        
        for roi in roi_values:
            cumulative += roi
            if cumulative < max_dd:
                max_dd = cumulative
            if cumulative > 0:
                cumulative = 0.0  # Reset on positive
        
        return abs(max_dd)
    
    def calculate_consistency_score(
        self,
        roi_values: List[float]
    ) -> float:
        """
        Consistency score: 1 / (1 + coefficient_of_variation)
        Higher is better - indicates more stable returns
        Range: 0 to 1
        """
        if not roi_values or len(roi_values) < 2:
            return 0.0
        
        mean_roi = np.mean(roi_values)
        std_roi = np.std(roi_values)
        
        if mean_roi == 0:
            return 0.0
        
        cv = std_roi / abs(mean_roi)  # Coefficient of variation
        return 1.0 / (1.0 + cv)
    
    def calculate_composite_score(
        self,
        roi_values: List[float],
        weights: Dict[str, float] = None
    ) -> float:
        """
        Composite score combining multiple metrics:
        - ROI (40%)
        - Sharpe-like ratio (25%)
        - Win rate (20%)
        - Consistency (15%)
        
        Returns normalized score 0-100
        """
        if weights is None:
            weights = {
                'roi': 0.40,
                'sharpe': 0.25,
                'win_rate': 0.20,
                'consistency': 0.15
            }
        
        # Normalize each metric to 0-1 scale
        mean_roi = np.mean(roi_values) if roi_values else 0.0
        sharpe = self.calculate_sharpe_like_ratio(roi_values)
        win_rate = self.calculate_win_rate(roi_values)
        consistency = self.calculate_consistency_score(roi_values)
        
        # Normalize ROI (assume range -1 to 2, adjust as needed)
        normalized_roi = max(0, min(1, (mean_roi + 1) / 3))
        
        # Normalize Sharpe (assume range -2 to 5)
        normalized_sharpe = max(0, min(1, (sharpe + 2) / 7))
        
        # Calculate weighted composite
        composite = (
            weights['roi'] * normalized_roi +
            weights['sharpe'] * normalized_sharpe +
            weights['win_rate'] * win_rate +
            weights['consistency'] * consistency
        )
        
        return composite * 100  # Scale to 0-100
```

### 3.2 Integration with Grid Search

**Update Grid Search Service**:
- Replace ROI-only optimization with composite score
- Add risk metrics to grid search results
- Store risk metrics in database

**Update Best Result Selection**:
```python
def _find_best_result(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Find best result using composite score instead of just ROI
    """
    for result in results:
        roi_values = self._extract_roi_values(result)
        result['composite_score'] = self.risk_calculator.calculate_composite_score(roi_values)
        result['sharpe'] = self.risk_calculator.calculate_sharpe_like_ratio(roi_values)
        result['win_rate'] = self.risk_calculator.calculate_win_rate(roi_values)
        result['consistency'] = self.risk_calculator.calculate_consistency_score(roi_values)
    
    # Sort by composite score instead of ROI
    best_result = max(results, key=lambda x: x.get('composite_score', x.get('roi', 0)))
    return best_result
```

### 3.3 Database Schema Updates

**Add to Prediction Model**:
```python
# Add columns to predictions table
sharpe_ratio = Column(Float, nullable=True)
win_rate = Column(Float, nullable=True)
consistency_score = Column(Float, nullable=True)
max_drawdown = Column(Float, nullable=True)
composite_score = Column(Float, nullable=True)
```

**Migration Script**:
```sql
ALTER TABLE predictions 
ADD COLUMN sharpe_ratio FLOAT,
ADD COLUMN win_rate FLOAT,
ADD COLUMN consistency_score FLOAT,
ADD COLUMN max_drawdown FLOAT,
ADD COLUMN composite_score FLOAT;
```

### 3.4 API Updates

**Update Simulation Endpoint**:
- Return risk metrics in response
- Add parameter to choose optimization metric (roi, composite, sharpe)

**New Analytics Endpoint**: `/api/analytics/risk-metrics`
- Returns risk metrics for all algorithms
- Compare algorithms by different risk metrics
- Identify low-risk, high-return algorithms

### 3.5 Configuration

**Add to Config**:
```python
# Risk metric weights for composite score
RISK_METRIC_WEIGHTS = {
    'roi': 0.40,
    'sharpe': 0.25,
    'win_rate': 0.20,
    'consistency': 0.15
}

# Risk thresholds
MIN_SHARPE_RATIO = 0.5
MIN_WIN_RATE = 0.40
MAX_DRAWDOWN_THRESHOLD = 0.50  # 50% max drawdown
```

### 3.6 Expected Outcomes

- **Better Algorithm Selection**: 10-15% improvement by selecting consistent performers
- **Risk Reduction**: 20-30% reduction in variance
- **Stability**: More predictable weekly performance
- **Drawdown Protection**: Avoid algorithms with high drawdown risk

### 3.7 Implementation Steps

1. Create `RiskMetricsCalculator` class
2. Add risk metric calculations to simulation engine
3. Update grid search to use composite score
4. Add database columns for risk metrics
5. Update API endpoints to return risk metrics
6. Add risk-based filtering to algorithm selection
7. Create risk analytics dashboard
8. Test and validate metrics
9. Deploy and monitor

### 3.8 Dependencies

- NumPy for statistical calculations
- Database schema updates
- Integration with grid search and simulation engine

### 3.9 Rollout Plan

1. **Phase 1**: Implement risk calculator (1 day)
2. **Phase 2**: Integrate with grid search (1 day)
3. **Phase 3**: Add database columns and migration (1 day)
4. **Phase 4**: Update APIs and test (1 day)
5. **Phase 5**: Deploy and monitor (ongoing)

