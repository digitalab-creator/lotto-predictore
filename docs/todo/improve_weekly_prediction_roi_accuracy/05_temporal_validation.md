# 5. Temporal Validation & Walk-Forward Analysis

**Priority: SHOULD HAVE**  
**Impact: Medium**  
**Effort: Medium**

## Problem Statement

Current validation only tests algorithms on a single time period, which has limitations:

1. **No Temporal Validation**: Algorithms might work well in one period but fail in others
2. **Overfitting Risk**: Good performance on test set doesn't guarantee future performance
3. **No Stability Check**: Can't verify algorithms maintain performance over time
4. **Seasonal Patterns**: Missing opportunities to identify time-based patterns

## Solution Overview

Implement temporal validation using walk-forward analysis:
- Test algorithms on rolling time windows
- Verify performance consistency across different periods
- Identify seasonal or time-based patterns
- Only use algorithms that pass temporal validation

## Implementation Details

### 5.1 Temporal Validator Service

**File**: `backend/services/core/temporal_validator.py`

```python
class TemporalValidator:
    """
    Validates algorithm performance across different time periods
    using walk-forward analysis.
    """
    
    def __init__(self, db: Session, simulation_engine: SimulationEngine):
        self.db = db
        self.engine = simulation_engine
    
    def walk_forward_analysis(
        self,
        draws: List[Draw],
        main_algo: str,
        strong_algo: str,
        window_size_weeks: int = 24,
        step_size_weeks: int = 4,
        min_windows: int = 3
    ) -> Dict[str, Any]:
        """
        Perform walk-forward analysis:
        1. Divide data into rolling windows
        2. For each window, train on first part, test on last part
        3. Track performance across all windows
        4. Calculate stability metrics
        
        Returns validation results with pass/fail status
        """
        windows = self._create_windows(
            draws, window_size_weeks, step_size_weeks
        )
        
        if len(windows) < min_windows:
            return {
                'valid': False,
                'reason': f'Insufficient data: {len(windows)} windows (need {min_windows})'
            }
        
        window_results = []
        for window in windows:
            result = self._evaluate_window(
                window, main_algo, strong_algo
            )
            window_results.append(result)
        
        # Calculate stability metrics
        stability = self._calculate_stability(window_results)
        
        # Determine if passes validation
        passes = self._validate_stability(stability)
        
        return {
            'valid': passes,
            'stability': stability,
            'window_results': window_results,
            'total_windows': len(windows)
        }
    
    def _create_windows(
        self,
        draws: List[Draw],
        window_size_weeks: int,
        step_size_weeks: int
    ) -> List[Dict[str, Any]]:
        """
        Create rolling time windows for walk-forward analysis.
        """
        windows = []
        total_weeks = len(draws) // 2  # Assuming 2 draws per week
        
        for start_week in range(0, total_weeks - window_size_weeks, step_size_weeks):
            end_week = start_week + window_size_weeks
            train_end_week = start_week + (window_size_weeks * 2 // 3)  # 2/3 for training
            
            # Convert weeks to draw indices
            start_idx = start_week * 2
            train_end_idx = train_end_week * 2
            end_idx = end_week * 2
            
            if end_idx > len(draws):
                break
            
            windows.append({
                'start_idx': start_idx,
                'train_end_idx': train_end_idx,
                'end_idx': end_idx,
                'train_draws': draws[start_idx:train_end_idx],
                'test_draws': draws[train_end_idx:end_idx]
            })
        
        return windows
    
    def _evaluate_window(
        self,
        window: Dict[str, Any],
        main_algo: str,
        strong_algo: str
    ) -> Dict[str, Any]:
        """
        Evaluate algorithm performance on a single window.
        """
        train_draws = window['train_draws']
        test_draws = window['test_draws']
        
        if len(train_draws) < 20 or len(test_draws) < 4:
            return {'valid': False, 'reason': 'Insufficient data'}
        
        train_start = train_draws[0].date
        train_end = train_draws[-1].date
        test_count = len(test_draws)
        
        # Run simulation
        results = self.engine.run_comparison(
            train_start=train_start,
            train_end=train_end,
            test_count=test_count,
            top_n=3,
            algo_names=[main_algo],
            strong_algo_names=[strong_algo]
        )
        
        if not results:
            return {'valid': False, 'reason': 'No results'}
        
        # Extract metrics
        roi_values = self._extract_roi_values(results)
        risk_calculator = RiskMetricsCalculator()
        
        return {
            'valid': True,
            'roi': np.mean(roi_values),
            'sharpe': risk_calculator.calculate_sharpe_like_ratio(roi_values),
            'win_rate': risk_calculator.calculate_win_rate(roi_values),
            'composite_score': risk_calculator.calculate_composite_score(roi_values),
            'period': f"{train_start} to {test_draws[-1].date}"
        }
    
    def _calculate_stability(
        self,
        window_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate stability metrics across windows:
        - Coefficient of variation (lower is better)
        - Percentage of profitable windows
        - Trend (improving/degrading)
        """
        valid_results = [r for r in window_results if r.get('valid')]
        
        if not valid_results:
            return {'stable': False, 'reason': 'No valid results'}
        
        rois = [r['roi'] for r in valid_results]
        composite_scores = [r['composite_score'] for r in valid_results]
        
        # Coefficient of variation
        roi_cv = np.std(rois) / abs(np.mean(rois)) if np.mean(rois) != 0 else float('inf')
        score_cv = np.std(composite_scores) / abs(np.mean(composite_scores)) if np.mean(composite_scores) != 0 else float('inf')
        
        # Profitability rate
        profitable_windows = sum(1 for r in rois if r > 0)
        profitability_rate = profitable_windows / len(rois)
        
        # Trend (simple linear regression)
        trend = self._calculate_trend(rois)
        
        return {
            'roi_cv': roi_cv,
            'score_cv': score_cv,
            'profitability_rate': profitability_rate,
            'trend': trend,
            'avg_roi': np.mean(rois),
            'avg_composite': np.mean(composite_scores),
            'total_windows': len(valid_results)
        }
    
    def _validate_stability(
        self,
        stability: Dict[str, float]
    ) -> bool:
        """
        Determine if algorithm passes temporal validation.
        Criteria:
        - ROI CV < 1.0 (not too volatile)
        - Profitability rate >= 60%
        - Trend not significantly negative
        - Average composite score > 50
        """
        if stability.get('roi_cv', float('inf')) > 1.0:
            return False
        
        if stability.get('profitability_rate', 0) < 0.60:
            return False
        
        if stability.get('trend', 0) < -0.1:  # Degrading more than 10% per window
            return False
        
        if stability.get('avg_composite', 0) < 50:
            return False
        
        return True
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate linear trend (slope) of values over time.
        Positive = improving, Negative = degrading
        """
        if len(values) < 2:
            return 0.0
        
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        return slope
```

### 5.2 Integration with Algorithm Selection

**Pre-Selection Filter**:
- Run temporal validation on candidate algorithms
- Only include algorithms that pass validation
- Prioritize algorithms with better stability scores

**Update Weekly Generation**:
```python
# Before selecting algorithms, validate them
validator = TemporalValidator(db, engine)
validated_algorithms = []

for algo_pair in candidate_algorithms:
    validation = validator.walk_forward_analysis(
        draws, algo_pair['main'], algo_pair['strong']
    )
    if validation['valid']:
        validated_algorithms.append({
            **algo_pair,
            'stability_score': validation['stability']['avg_composite']
        })

# Use only validated algorithms
```

### 5.3 Database Tracking

**New Table**: `temporal_validations`
```sql
CREATE TABLE temporal_validations (
    id SERIAL PRIMARY KEY,
    main_algo VARCHAR(255) NOT NULL,
    strong_algo VARCHAR(255) NOT NULL,
    validation_date TIMESTAMP DEFAULT NOW(),
    valid BOOLEAN NOT NULL,
    stability_metrics JSONB,
    window_results JSONB,
    total_windows INTEGER,
    notes TEXT
);

CREATE INDEX idx_temp_val_algo ON temporal_validations(main_algo, strong_algo);
CREATE INDEX idx_temp_val_date ON temporal_validations(validation_date DESC);
```

### 5.4 Expected Outcomes

- **Stability**: 20-30% reduction in performance variance
- **Reliability**: Only use algorithms proven to work across time
- **Pattern Discovery**: Identify seasonal or time-based patterns
- **Risk Reduction**: Avoid algorithms that degrade over time

### 5.5 Implementation Steps

1. Create `TemporalValidator` class
2. Implement walk-forward analysis
3. Add stability metrics calculation
4. Integrate with algorithm selection
5. Add database tracking
6. Create validation cron job (optional)
7. Test with historical data
8. Deploy and monitor

### 5.6 Dependencies

- Simulation engine
- Risk metrics calculator
- NumPy for statistical calculations

### 5.7 Rollout Plan

1. **Phase 1**: Implement validator (2 days)
2. **Phase 2**: Integrate with selection (1 day)
3. **Phase 3**: Add tracking and test (2 days)
4. **Phase 4**: Deploy and monitor (ongoing)


