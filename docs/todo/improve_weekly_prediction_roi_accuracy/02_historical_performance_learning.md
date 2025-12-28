# 2. Historical Performance Learning

**Priority: MUST HAVE**  
**Impact: High**  
**Effort: Medium**

## Problem Statement

The system currently tracks prediction results in `PredictionDetail` but doesn't use this valuable data to improve future predictions. Key issues:

1. **No Learning from History**: Algorithm selection doesn't consider how algorithms actually performed in production
2. **No Performance Tracking**: Can't identify which algorithms degrade over time
3. **No Pattern Recognition**: Missing opportunities to identify when certain algorithms work better
4. **Static Evaluation**: Grid search uses simulated ROI, not actual production performance

## Solution Overview

Create a performance analyzer that:
- Analyzes historical `PredictionDetail` records to track actual algorithm performance
- Identifies performance trends and degradation patterns
- Adjusts algorithm weights based on recent vs historical performance
- Discovers patterns in successful predictions (time-based, seasonal, etc.)

## Implementation Details

### 2.1 Performance Analyzer Architecture

**File**: `backend/services/core/performance_analyzer.py`

```python
class PerformanceAnalyzer:
    """
    Analyzes historical prediction performance to improve future predictions.
    Tracks algorithm performance over time and identifies patterns.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_algorithm_performance(
        self,
        main_algo: str,
        strong_algo: str,
        lookback_weeks: int = 12
    ) -> Dict[str, Any]:
        """
        Analyze performance of specific algorithm pair:
        - ROI over time (trend analysis)
        - Hit rate distribution
        - Strong number accuracy
        - Consistency metrics
        - Performance degradation detection
        """
        pass
    
    def get_algorithm_rankings(
        self,
        lookback_weeks: int = 12,
        min_predictions: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rank all algorithm pairs by:
        1. Recent ROI (last 4 weeks)
        2. Historical ROI (all time)
        3. Consistency (low variance)
        4. Win rate
        5. Strong number accuracy
        
        Returns sorted list with scores
        """
        pass
    
    def detect_performance_degradation(
        self,
        main_algo: str,
        strong_algo: str,
        threshold: float = 0.2
    ) -> bool:
        """
        Detect if algorithm performance is degrading:
        - Compare recent ROI (last 4 weeks) vs historical (last 12 weeks)
        - Flag if recent performance drops > threshold
        """
        pass
    
    def identify_seasonal_patterns(
        self,
        main_algo: str,
        strong_algo: str
    ) -> Dict[str, Any]:
        """
        Identify if algorithm performs better in:
        - Certain days of week
        - Certain months
        - Certain time periods
        """
        pass
    
    def calculate_adaptive_weights(
        self,
        algorithm_pairs: List[Tuple[str, str]],
        recency_weight: float = 0.6
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate adaptive weights that balance:
        - Recent performance (recency_weight)
        - Historical performance (1 - recency_weight)
        - Consistency bonus
        - Degradation penalty
        """
        pass
```

### 2.2 Performance Metrics to Track

**Per-Algorithm Metrics**:
- **ROI**: Average ROI per draw
- **Hit Rate**: Average number of hits per combination
- **Strong Accuracy**: Percentage of correct strong number predictions
- **Win Rate**: Percentage of draws with positive ROI
- **Consistency**: Standard deviation of ROI (lower is better)
- **Max Drawdown**: Worst consecutive losing streak
- **Recovery Time**: Time to recover from drawdown

**Time-Based Analysis**:
- Performance by day of week
- Performance by month/season
- Performance trends (improving/degrading)
- Performance stability over rolling windows

### 2.3 Database Queries

**Performance Summary Query**:
```sql
SELECT 
    m.name as main_algo,
    sm.name as strong_algo,
    COUNT(DISTINCT pd.prediction_id) as prediction_count,
    AVG(pd.roi) as avg_roi,
    STDDEV(pd.roi) as roi_stddev,
    AVG(pd.hits) as avg_hits,
    AVG(CASE WHEN pd.strong_hit = 1 THEN 1.0 ELSE 0.0 END) as strong_accuracy,
    SUM(CASE WHEN pd.roi > 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as win_rate,
    MIN(pd.roi) as min_roi,
    MAX(pd.roi) as max_roi
FROM prediction_details pd
JOIN predictions p ON pd.prediction_id = p.id
JOIN models m ON p.model_id = m.id
JOIN models sm ON p.strong_model_id = sm.id
WHERE pd.test_draw_date >= NOW() - INTERVAL '12 weeks'
GROUP BY m.name, sm.name
HAVING COUNT(*) >= 10
ORDER BY avg_roi DESC;
```

**Time-Based Performance Query**:
```sql
SELECT 
    DATE_TRUNC('week', pd.test_draw_date) as week,
    m.name as main_algo,
    sm.name as strong_algo,
    AVG(pd.roi) as weekly_roi,
    COUNT(*) as draw_count
FROM prediction_details pd
JOIN predictions p ON pd.prediction_id = p.id
JOIN models m ON p.model_id = m.id
JOIN models sm ON p.strong_model_id = sm.id
WHERE pd.test_draw_date >= NOW() - INTERVAL '24 weeks'
GROUP BY week, m.name, sm.name
ORDER BY week DESC, weekly_roi DESC;
```

### 2.4 Integration with Grid Search

**Update Grid Search**:
- Use historical performance to seed algorithm rankings
- Prioritize algorithms with good historical track record
- Penalize algorithms with recent degradation
- Use adaptive test_count based on algorithm stability

**Update Algorithm Selection**:
- Weight recent performance more heavily (60-70%)
- Consider historical consistency
- Exclude algorithms with significant degradation

### 2.5 Performance Dashboard

**New Endpoint**: `/api/analytics/algorithm-performance`

Returns:
- Algorithm rankings with all metrics
- Performance trends over time
- Degradation alerts
- Seasonal patterns
- Recommendations for algorithm selection

### 2.6 Automated Learning Loop

**Cron Job**: `validate_and_learn.py`
- Runs after each draw
- Updates performance metrics
- Detects degradation
- Adjusts algorithm weights
- Triggers re-optimization if needed

### 2.7 Expected Outcomes

- **Better Algorithm Selection**: 15-25% improvement by using actual performance data
- **Early Degradation Detection**: Identify underperforming algorithms before they cause significant losses
- **Adaptive Optimization**: System automatically adjusts to changing patterns
- **Pattern Discovery**: Identify when certain algorithms work best

### 2.8 Implementation Steps

1. Create `PerformanceAnalyzer` class
2. Implement database queries for performance analysis
3. Add performance tracking to prediction storage
4. Create performance dashboard endpoint
5. Integrate with grid search and ensemble service
6. Create automated learning cron job
7. Add degradation detection alerts
8. Test with historical data
9. Deploy and monitor

### 2.9 Dependencies

- PredictionDetail data (already exists)
- Database access
- Time series analysis libraries (optional)

### 2.10 Rollout Plan

1. **Phase 1**: Implement analyzer and test queries (3 days)
2. **Phase 2**: Integrate with algorithm selection (2 days)
3. **Phase 3**: Add dashboard and monitoring (2 days)
4. **Phase 4**: Deploy automated learning loop (1 day)
5. **Phase 5**: Monitor and optimize (ongoing)

