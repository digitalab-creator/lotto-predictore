# 4. Adaptive Parameter Optimization

**Priority: SHOULD HAVE**  
**Impact: Medium-High**  
**Effort: Medium-High**

## Problem Statement

Current grid search uses fixed parameter ranges and brute-force search:

1. **Fixed Ranges**: Parameter ranges don't adapt based on what works
2. **Brute Force**: Tests all combinations, inefficient for large search spaces
3. **No Learning**: Doesn't learn which parameter ranges work best for each algorithm
4. **One-Size-Fits-All**: Same parameter ranges for all algorithms, even though they may need different values

## Solution Overview

Implement adaptive parameter optimization that:
- Learns optimal parameter ranges from historical performance
- Uses Bayesian optimization for efficient search
- Adapts parameter ranges per algorithm based on historical success
- Reduces search space while improving results

## Implementation Details

### 4.1 Bayesian Optimizer

**File**: `backend/services/core/bayesian_optimizer.py`

```python
from skopt import gp_minimize
from skopt.space import Real, Integer
from skopt.utils import use_named_args

class BayesianParameterOptimizer:
    """
    Uses Bayesian optimization (Gaussian Process) to efficiently
    find optimal parameters without brute-force grid search.
    """
    
    def __init__(self, db: Session, simulation_engine: SimulationEngine):
        self.db = db
        self.engine = simulation_engine
        self.performance_analyzer = PerformanceAnalyzer(db)
    
    def optimize_parameters(
        self,
        draws: List[Draw],
        main_algo: str,
        strong_algo: str,
        n_calls: int = 30,
        n_initial_points: int = 10
    ) -> Dict[str, Any]:
        """
        Optimize parameters using Bayesian optimization:
        1. Define parameter search space (adaptive based on historical data)
        2. Use Gaussian Process to model objective function
        3. Use acquisition function to select next points to evaluate
        4. Iteratively improve until convergence or max iterations
        """
        # Get historical optimal ranges for this algorithm
        historical_ranges = self._get_historical_ranges(main_algo, strong_algo)
        
        # Define search space
        search_space = self._define_search_space(historical_ranges)
        
        # Define objective function (negative composite score to minimize)
        @use_named_args(dimensions=search_space)
        def objective(**params):
            return -self._evaluate_parameters(
                draws, main_algo, strong_algo, params
            )
        
        # Run optimization
        result = gp_minimize(
            func=objective,
            dimensions=search_space,
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            acq_func='EI'  # Expected Improvement
        )
        
        # Extract best parameters
        best_params = dict(zip(
            [dim.name for dim in search_space],
            result.x
        ))
        
        return {
            'parameters': best_params,
            'best_score': -result.fun,
            'optimization_history': result.func_vals,
            'n_iterations': len(result.func_vals)
        }
    
    def _get_historical_ranges(
        self,
        main_algo: str,
        strong_algo: str
    ) -> Dict[str, Tuple[float, float]]:
        """
        Get historical optimal parameter ranges for algorithm pair.
        Uses performance analyzer to find what worked best in the past.
        """
        # Query historical predictions with this algorithm pair
        # Extract parameter values and their performance
        # Return optimal ranges (min, max) for each parameter
        pass
    
    def _define_search_space(
        self,
        historical_ranges: Dict[str, Tuple[float, float]]
    ) -> List:
        """
        Define search space based on historical ranges.
        Expands ranges slightly to allow exploration.
        """
        space = [
            Integer(
                name='top_n',
                low=max(2, historical_ranges.get('top_n', (3, 5))[0] - 1),
                high=min(10, historical_ranges.get('top_n', (3, 5))[1] + 2)
            ),
            Integer(
                name='num_to_recommend',
                low=max(3, historical_ranges.get('num_to_recommend', (5, 10))[0] - 2),
                high=min(15, historical_ranges.get('num_to_recommend', (5, 10))[1] + 3)
            ),
            Integer(
                name='test_count',
                low=max(8, historical_ranges.get('test_count', (10, 15))[0] - 2),
                high=min(20, historical_ranges.get('test_count', (10, 15))[1] + 3)
            )
        ]
        return space
    
    def _evaluate_parameters(
        self,
        draws: List[Draw],
        main_algo: str,
        strong_algo: str,
        params: Dict[str, Any]
    ) -> float:
        """
        Evaluate parameter combination and return composite score.
        """
        # Split data
        test_count = params['test_count']
        train_draws = draws[:-test_count]
        train_start = train_draws[0].date
        train_end = train_draws[-1].date
        
        # Run simulation
        results = self.engine.run_comparison(
            train_start=train_start,
            train_end=train_end,
            test_count=test_count,
            top_n=params['top_n'],
            algo_names=[main_algo],
            strong_algo_names=[strong_algo]
        )
        
        # Extract ROI values and calculate composite score
        if results:
            roi_values = self._extract_roi_values(results)
            risk_calculator = RiskMetricsCalculator()
            return risk_calculator.calculate_composite_score(roi_values)
        
        return 0.0
```

### 4.2 Parameter Performance Tracking

**New Table**: `parameter_performance`
```sql
CREATE TABLE parameter_performance (
    id SERIAL PRIMARY KEY,
    main_algo VARCHAR(255) NOT NULL,
    strong_algo VARCHAR(255) NOT NULL,
    top_n INTEGER NOT NULL,
    num_to_recommend INTEGER NOT NULL,
    test_count INTEGER NOT NULL,
    prediction_id INTEGER REFERENCES predictions(id),
    roi FLOAT NOT NULL,
    composite_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(main_algo, strong_algo, top_n, num_to_recommend, test_count, prediction_id)
);

CREATE INDEX idx_param_perf_algo ON parameter_performance(main_algo, strong_algo);
CREATE INDEX idx_param_perf_score ON parameter_performance(composite_score DESC);
```

### 4.3 Adaptive Range Learning

**File**: `backend/services/core/parameter_range_learner.py`

```python
class ParameterRangeLearner:
    """
    Learns optimal parameter ranges for each algorithm based on historical performance.
    """
    
    def learn_optimal_ranges(
        self,
        main_algo: str,
        strong_algo: str,
        min_samples: int = 20
    ) -> Dict[str, Tuple[float, float]]:
        """
        Analyze historical parameter performance to find optimal ranges.
        Returns (min, max) for each parameter.
        """
        # Query parameter_performance table
        # Group by parameter values
        # Find ranges where performance is consistently good
        # Return optimal ranges
        pass
    
    def update_ranges_from_prediction(
        self,
        prediction: Prediction,
        performance_metrics: Dict[str, float]
    ):
        """
        Update parameter ranges based on new prediction results.
        """
        # Store parameter combination and performance
        # Update optimal ranges if this is better
        pass
```

### 4.4 Integration with Grid Search

**Hybrid Approach**:
- Use Bayesian optimization for initial search (faster)
- Use grid search for fine-tuning around optimal region
- Combine both approaches for best results

**Update Grid Search**:
- Use learned parameter ranges instead of fixed ranges
- Focus search around Bayesian-optimized region
- Reduce search space while maintaining coverage

### 4.5 Expected Outcomes

- **Faster Optimization**: 50-70% reduction in search time
- **Better Results**: 5-10% improvement in optimal parameters
- **Adaptive Learning**: System learns optimal ranges per algorithm
- **Efficiency**: Focus search on promising regions

### 4.6 Implementation Steps

1. Install scikit-optimize library
2. Create `BayesianParameterOptimizer` class
3. Create `ParameterRangeLearner` class
4. Add parameter_performance table
5. Integrate with grid search service
6. Update weekly generation to use adaptive optimization
7. Add parameter tracking to prediction storage
8. Test and validate
9. Deploy and monitor

### 4.7 Dependencies

- scikit-optimize library
- Performance analyzer (for historical data)
- Risk metrics calculator
- Database schema updates

### 4.8 Rollout Plan

1. **Phase 1**: Implement Bayesian optimizer (3 days)
2. **Phase 2**: Add parameter tracking (2 days)
3. **Phase 3**: Integrate with grid search (2 days)
4. **Phase 4**: Test and optimize (2 days)
5. **Phase 5**: Deploy and monitor (ongoing)

