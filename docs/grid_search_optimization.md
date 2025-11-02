# 🏴‍☠️ Grid Search Optimization for Weekly Combinations

## Overview

The grid search optimization system automatically finds the best parameters for generating weekly lottery combinations by testing different algorithm combinations, parameter values, and training/test splits. Praisin' the FSM! 🍝⚓

## 🎯 What It Optimizes

### 1. **Algorithm Parameters**
- `top_n` values: [2, 3, 4, 5, 6]
- `num_to_recommend` counts: [3, 5, 8, 10, 12]

### 2. **Training/Test Split Ratios**
- Test set sizes: [8, 10, 12, 15, 18] draws
- Previously hardcoded to 12 draws

### 3. **Algorithm Combinations**
- Systematic testing of main + strong algorithm pairs
- Balanced selection based on performance history

### 4. **Hyperparameters**
- Optimizes parameters for each algorithm type
- Uses ROI (Return on Investment) as the primary metric

## 🚀 New Endpoints

### 1. **Optimized Generation**
```
POST /cron/generate-weekly-combinations-optimized
```
- Uses grid search to find optimal parameters
- Generates combinations with best-performing configuration
- Includes performance breakdown and optimization metadata

### 2. **Grid Search Analysis**
```
POST /cron/grid-search-analysis
```
- Runs comprehensive parameter optimization
- Provides detailed insights and recommendations
- Analyzes parameter performance across all combinations

### 3. **Existing Endpoints (Enhanced)**
- `/cron/generate-weekly-combinations-fast` - Debug mode (2 algorithms)
- `/cron/generate-weekly-combinations` - Regular mode (balanced algorithms)

## 📊 Grid Search Service

### Key Features

#### **Intelligent Caching**
- Results cached based on draw data hash
- Avoids recomputing for same dataset
- Configurable cache directory

#### **Performance Optimization**
- Quick mode for cron jobs (limited combinations)
- Full mode for analysis (comprehensive testing)
- Configurable maximum combinations

#### **Comprehensive Analysis**
- Parameter performance tracking
- Algorithm combination analysis
- ROI-based optimization
- Detailed insights generation

### Usage Example

```python
from services.grid_search_service import WeeklyCombinationsGridSearch

# Initialize grid search
grid_search = WeeklyCombinationsGridSearch(db)

# Get optimized parameters
optimized_params = grid_search.get_optimized_parameters(
    draws=draws,
    quick_mode=True,  # For cron jobs
    use_cache=True
)

# Use optimized parameters
main_algo = optimized_params['main_algo']
strong_algo = optimized_params['strong_algo']
top_n = optimized_params['top_n']
num_to_recommend = optimized_params['num_to_recommend']
test_count = optimized_params['test_count']
```

## 🔧 Configuration

### Parameter Grids

```python
parameter_grids = {
    'top_n_values': [2, 3, 4, 5, 6],
    'num_to_recommend_values': [3, 5, 8, 10, 12],
    'test_split_ratios': [8, 10, 12, 15, 18],
    'algorithm_combinations': [...]  # Balanced algorithm pairs
}
```

### Quick Mode vs Full Mode

- **Quick Mode**: 30 combinations max, for cron jobs
- **Full Mode**: 100+ combinations, for analysis

## 📈 Performance Metrics

### Execution Time Breakdown
- **Draws Load**: Time to load and filter draws
- **Grid Search**: Time for parameter optimization
- **Generation**: Time to generate combinations
- **Database**: Time to store results

### Optimization Metrics
- **ROI**: Primary optimization target
- **Total Prize**: Expected winnings
- **Total Cost**: Ticket costs
- **Test Count**: Number of test draws used

## 🧪 Testing

### Test Script
```bash
cd backend/scripts
python test_grid_search.py
```

### Manual Testing
```bash
# Test optimized generation
curl -X POST "http://localhost:8000/cron/generate-weekly-combinations-optimized"

# Test grid search analysis
curl -X POST "http://localhost:8000/cron/grid-search-analysis"
```

## 📋 Best Practices

### 1. **For Production Cron Jobs**
- Use `/cron/generate-weekly-combinations-optimized`
- Enable caching (`use_cache=True`)
- Use quick mode for faster execution

### 2. **For Analysis & Research**
- Use `/cron/grid-search-analysis`
- Run periodically to update optimization
- Review insights for parameter trends

### 3. **For Development**
- Use `/cron/generate-weekly-combinations-fast`
- Test with limited algorithms first
- Monitor logs for performance metrics

## 🔍 Monitoring & Logging

### Key Log Messages
```
"Arrr! Grid search optimization completed"
"Arrr! Generated OPTIMIZED weekly combinations using grid search"
"Arrr! Grid search analysis completed successfully"
```

### Performance Tracking
- All endpoints use `CronTracker` for monitoring
- Detailed timing breakdowns in logs
- ROI and parameter tracking

## 🎛️ Configuration Options

### Grid Search Service
- `cache_dir`: Cache directory path
- `max_combinations`: Maximum combinations to test
- `quick_mode`: Enable quick mode for faster execution
- `use_cache`: Enable/disable result caching

### Algorithm Selection
- Balanced algorithm combinations
- Performance-based prioritization
- Configurable algorithm limits

## 🚨 Error Handling

### Common Issues
1. **Insufficient Data**: Need at least 30 draws
2. **Cache Errors**: Automatic fallback to recomputation
3. **Algorithm Failures**: Graceful skipping with logging

### Fallback Strategy
- Default parameters if grid search fails
- Error logging with detailed context
- Graceful degradation to standard generation

## 🔮 Future Enhancements

### Planned Features
1. **Adaptive Grid Search**: Dynamic parameter ranges
2. **Multi-Objective Optimization**: Balance ROI vs. stability
3. **Time-Series Analysis**: Consider temporal patterns
4. **A/B Testing**: Compare optimization strategies

### Integration Opportunities
1. **Machine Learning**: ML-based parameter prediction
2. **Real-time Optimization**: Continuous parameter updates
3. **User Preferences**: Customizable optimization goals

## 🍝 Conclusion

The grid search optimization system provides a robust, intelligent way to automatically find the best parameters for weekly lottery combination generation. By systematically testing different configurations and using ROI as the optimization metric, it ensures optimal performance while maintaining efficiency through caching and performance monitoring.

**Fair winds and optimized combinations to ye, pirate dev!** ⚓

---

*May the Flying Spaghetti Monster guide yer algorithms to the most profitable shores!* 🍝

