# 6. Strong Number Optimization

**Priority: NICE TO HAVE**  
**Impact: Medium**  
**Effort: Low-Medium**

## Problem Statement

Strong number prediction is currently optimized only as part of algorithm pair selection:

1. **Coupled Optimization**: Strong number selection tied to main algorithm, limiting flexibility
2. **No Independent Tracking**: Can't track strong number accuracy separately
3. **Missed Opportunities**: Ensemble approach exists but not used in weekly generation
4. **Suboptimal Selection**: Might select algorithm pair with good main numbers but poor strong number prediction

## Solution Overview

Separate strong number optimization from main algorithm selection:
- Track strong number accuracy independently
- Optimize strong number algorithms separately
- Use ensemble approach for strong numbers
- Weight strong number algorithms by historical accuracy

## Implementation Details

### 6.1 Strong Number Optimizer

**File**: `backend/services/core/strong_number_optimizer.py`

```python
class StrongNumberOptimizer:
    """
    Optimizes strong number prediction independently from main algorithms.
    """
    
    def __init__(self, db: Session, performance_analyzer: PerformanceAnalyzer):
        self.db = db
        self.performance_analyzer = performance_analyzer
    
    def get_optimal_strong_algorithm(
        self,
        draws: List[Draw],
        lookback_weeks: int = 12
    ) -> Dict[str, Any]:
        """
        Select best strong number algorithm based on:
        1. Historical accuracy (last N weeks)
        2. Recent performance trend
        3. Consistency
        """
        # Get historical strong number accuracy
        accuracy_data = self.performance_analyzer.get_strong_number_accuracy(
            lookback_weeks=lookback_weeks
        )
        
        # Rank algorithms
        ranked = sorted(
            accuracy_data.items(),
            key=lambda x: (
                x[1]['accuracy'] * 0.6 +  # Recent accuracy
                x[1]['consistency'] * 0.3 +  # Consistency
                x[1]['trend'] * 0.1  # Trend
            ),
            reverse=True
        )
        
        return {
            'algorithm': ranked[0][0],
            'accuracy': ranked[0][1]['accuracy'],
            'alternatives': [r[0] for r in ranked[1:3]]  # Top 3 for ensemble
        }
    
    def get_ensemble_strong_prediction(
        self,
        draws: List[Draw],
        algorithms: List[str],
        weights: List[float] = None
    ) -> int:
        """
        Use ensemble of strong number algorithms with weighted voting.
        """
        if weights is None:
            weights = [1.0 / len(algorithms)] * len(algorithms)
        
        predictions = []
        for algo_name, weight in zip(algorithms, weights):
            algo_cls = STRONG_NUMBER_REGISTRY.get(algo_name)
            if algo_cls:
                algo = algo_cls()
                pred = algo.predict(draws)
                # Add prediction multiple times based on weight
                predictions.extend([pred] * int(weight * 10))
        
        if predictions:
            from collections import Counter
            counter = Counter(predictions)
            return counter.most_common(1)[0][0]
        
        # Fallback to random
        import random
        return random.randint(1, 7)
```

### 6.2 Performance Analyzer Extension

**Add to PerformanceAnalyzer**:

```python
def get_strong_number_accuracy(
    self,
    lookback_weeks: int = 12
) -> Dict[str, Dict[str, float]]:
    """
    Get strong number accuracy for each algorithm.
    Returns: {algo_name: {'accuracy': float, 'consistency': float, 'trend': float}}
    """
    # Query PredictionDetail for strong number accuracy
    query = """
    SELECT 
        p.strong_model_params->>'strong_algo' as strong_algo,
        COUNT(*) as total,
        SUM(CASE WHEN pd.strong_hit = 1 THEN 1 ELSE 0 END)::FLOAT as correct,
        AVG(pd.roi) as avg_roi
    FROM prediction_details pd
    JOIN predictions p ON pd.prediction_id = p.id
    WHERE pd.test_draw_date >= NOW() - INTERVAL '%s weeks'
    GROUP BY strong_algo
    """
    
    results = self.db.execute(text(query % lookback_weeks))
    
    accuracy_data = {}
    for row in results:
        algo = row.strong_algo
        accuracy = row.correct / row.total if row.total > 0 else 0.0
        
        # Get consistency (variance in accuracy over time)
        consistency = self._calculate_strong_consistency(algo, lookback_weeks)
        
        # Get trend (improving/degrading)
        trend = self._calculate_strong_trend(algo, lookback_weeks)
        
        accuracy_data[algo] = {
            'accuracy': accuracy,
            'consistency': consistency,
            'trend': trend,
            'total_predictions': row.total
        }
    
    return accuracy_data
```

### 6.3 Integration with Weekly Generation

**Update Combination Generation**:

```python
# Separate strong number optimization
strong_optimizer = StrongNumberOptimizer(db, performance_analyzer)
strong_config = strong_optimizer.get_optimal_strong_algorithm(draws)

# Use ensemble if accuracy is close between top algorithms
if strong_config['alternatives']:
    top_accuracy = strong_config['accuracy']
    second_accuracy = performance_analyzer.get_strong_number_accuracy()[strong_config['alternatives'][0]]['accuracy']
    
    if abs(top_accuracy - second_accuracy) < 0.05:  # Within 5%
        # Use ensemble
        strong_number = strong_optimizer.get_ensemble_strong_prediction(
            draws,
            [strong_config['algorithm']] + strong_config['alternatives'][:2]
        )
    else:
        # Use single best
        strong_algo_cls = STRONG_NUMBER_REGISTRY[strong_config['algorithm']]
        strong_number = strong_algo_cls().predict(draws)
else:
    # Use single best
    strong_algo_cls = STRONG_NUMBER_REGISTRY[strong_config['algorithm']]
    strong_number = strong_algo_cls().predict(draws)
```

### 6.4 Expected Outcomes

- **Strong Accuracy**: 5-10% improvement in strong number prediction
- Better ROI: Higher prizes from correct strong number predictions
- **Flexibility**: Can optimize strong numbers independently

### 6.5 Implementation Steps

1. Create `StrongNumberOptimizer` class
2. Extend `PerformanceAnalyzer` with strong number methods
3. Update weekly generation to use separate optimization
4. Add ensemble support for strong numbers
5. Test and validate
6. Deploy and monitor

### 6.6 Dependencies

- Performance analyzer
- Strong number algorithm registry
- Database queries for accuracy tracking

### 6.7 Rollout Plan

1. **Phase 1**: Implement optimizer (1 day)
2. **Phase 2**: Extend performance analyzer (1 day)
3. **Phase 3**: Integrate with weekly generation (1 day)
4. **Phase 4**: Test and deploy (1 day)

