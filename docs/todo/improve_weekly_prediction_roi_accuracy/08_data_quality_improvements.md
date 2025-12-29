# 8. Data Quality Improvements

**Priority: NICE TO HAVE**  
**Impact: Low-Medium**  
**Effort: Low-Medium**

## Problem Statement

Current data filtering is simple (strong_number <= 7), but could be improved:

1. **No Outlier Detection**: Anomalous draws might skew predictions
2. **No Data Validation**: Missing checks for data quality issues
3. **Simple Filtering**: Only filters by strong_number, could use more sophisticated methods
4. **No Anomaly Detection**: Can't identify unusual patterns that might indicate data issues

## Solution Overview

Implement comprehensive data quality checks:
- Detect and handle outliers
- Validate data integrity
- Identify anomalous draws
- Use statistical tests to ensure data quality before training

## Implementation Details

### 8.1 Data Quality Service

**File**: `backend/services/core/data_quality.py`

```python
class DataQualityChecker:
    """
    Validates and cleans draw data before using for predictions.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_draws(
        self,
        draws: List[Draw],
        strict: bool = False
    ) -> Dict[str, Any]:
        """
        Validate draws for quality issues:
        - Missing or invalid numbers
        - Outlier detection
        - Pattern anomalies
        - Statistical consistency
        """
        issues = []
        warnings = []
        cleaned_draws = []
        
        for draw in draws:
            # Basic validation
            if not self._validate_basic(draw):
                issues.append({
                    'draw_id': draw.id,
                    'date': draw.date,
                    'issue': 'Basic validation failed'
                })
                continue
            
            # Outlier detection
            if self._is_outlier(draw, draws):
                if strict:
                    issues.append({
                        'draw_id': draw.id,
                        'date': draw.date,
                        'issue': 'Outlier detected'
                    })
                    continue
                else:
                    warnings.append({
                        'draw_id': draw.id,
                        'date': draw.date,
                        'warning': 'Outlier detected but included'
                    })
            
            # Pattern validation
            if not self._validate_patterns(draw, draws):
                warnings.append({
                    'draw_id': draw.id,
                    'date': draw.date,
                    'warning': 'Unusual pattern detected'
                })
            
            cleaned_draws.append(draw)
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'original_count': len(draws),
            'cleaned_count': len(cleaned_draws),
            'cleaned_draws': cleaned_draws
        }
    
    def _validate_basic(self, draw: Draw) -> bool:
        """
        Basic validation: numbers exist, are valid, strong_number valid.
        """
        if not hasattr(draw, 'numbers') or not draw.numbers:
            return False
        
        if len(draw.numbers) != 6:
            return False
        
        if not all(1 <= n <= 37 for n in draw.numbers):
            return False
        
        if hasattr(draw, 'strong_number'):
            if draw.strong_number not in range(1, 8):
                return False
        
        return True
    
    def _is_outlier(
        self,
        draw: Draw,
        all_draws: List[Draw]
    ) -> bool:
        """
        Detect if draw is statistical outlier using:
        - Z-score for number frequencies
        - Distance from mean pattern
        """
        if len(all_draws) < 20:
            return False  # Need enough data for outlier detection
        
        # Calculate number frequency distribution
        number_counts = {}
        for d in all_draws:
            for num in d.numbers:
                number_counts[num] = number_counts.get(num, 0) + 1
        
        # Calculate mean and std for each number
        mean_freq = np.mean(list(number_counts.values()))
        std_freq = np.std(list(number_counts.values()))
        
        # Check if this draw's numbers are outliers
        draw_freq_sum = sum(number_counts.get(n, 0) for n in draw.numbers)
        z_score = (draw_freq_sum - (mean_freq * 6)) / (std_freq * np.sqrt(6))
        
        # Flag as outlier if z-score > 2.5
        return abs(z_score) > 2.5
    
    def _validate_patterns(
        self,
        draw: Draw,
        all_draws: List[Draw]
    ) -> bool:
        """
        Validate that draw follows expected patterns:
        - Number spread (not all high or all low)
        - Consecutive numbers (some are OK, too many is suspicious)
        - Even/odd distribution
        """
        numbers = draw.numbers
        
        # Check spread (should have mix of low, mid, high)
        low = sum(1 for n in numbers if n <= 12)
        mid = sum(1 for n in numbers if 13 <= n <= 25)
        high = sum(1 for n in numbers if n >= 26)
        
        if low == 0 or mid == 0 or high == 0:
            return False  # Too concentrated
        
        # Check consecutive numbers (more than 3 consecutive is unusual)
        sorted_nums = sorted(numbers)
        consecutive_count = 0
        max_consecutive = 0
        
        for i in range(len(sorted_nums) - 1):
            if sorted_nums[i+1] - sorted_nums[i] == 1:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0
        
        if max_consecutive > 3:
            return False  # Too many consecutive
        
        return True
    
    def detect_anomalies(
        self,
        draws: List[Draw],
        window_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalous patterns in recent draws:
        - Unusual frequency changes
        - Pattern breaks
        - Statistical shifts
        """
        anomalies = []
        
        if len(draws) < window_size * 2:
            return anomalies
        
        # Compare recent window to historical
        recent = draws[-window_size:]
        historical = draws[-window_size*2:-window_size]
        
        # Compare number frequency distributions
        recent_freq = self._calculate_frequency_distribution(recent)
        historical_freq = self._calculate_frequency_distribution(historical)
        
        # Detect significant shifts
        for num in range(1, 38):
            recent_pct = recent_freq.get(num, 0) / window_size
            historical_pct = historical_freq.get(num, 0) / window_size
            
            if abs(recent_pct - historical_pct) > 0.15:  # 15% shift
                anomalies.append({
                    'type': 'frequency_shift',
                    'number': num,
                    'recent_pct': recent_pct,
                    'historical_pct': historical_pct,
                    'shift': recent_pct - historical_pct
                })
        
        return anomalies
    
    def _calculate_frequency_distribution(
        self,
        draws: List[Draw]
    ) -> Dict[int, int]:
        """
        Calculate frequency of each number in draws.
        """
        freq = {}
        for draw in draws:
            for num in draw.numbers:
                freq[num] = freq.get(num, 0) + 1
        return freq
```

### 8.2 Integration Points

**Update Base Combination Generator**:
```python
def load_draws_with_filter(db: Session):
    """
    Load draws with quality checks.
    """
    # Get all draws
    all_draws = db.query(Draw).filter(
        Draw.strong_number <= 7
    ).order_by(Draw.date).all()
    
    # Run quality checks
    quality_checker = DataQualityChecker(db)
    validation = quality_checker.validate_draws(all_draws, strict=False)
    
    if not validation['valid']:
        logger.warning(
            "Arrr! Data quality issues detected!",
            context={
                'issues': validation['issues'],
                'warnings': validation['warnings']
            }
        )
    
    return validation['cleaned_draws'], len(all_draws) - len(validation['cleaned_draws']), 0.0
```

### 8.3 Expected Outcomes

- **Better Data Quality**: Filter out problematic draws
- **More Reliable Predictions**: Predictions based on clean data
- **Anomaly Detection**: Identify unusual patterns early
- **Data Integrity**: Ensure data quality before training

### 8.4 Implementation Steps

1. Create `DataQualityChecker` class
2. Implement validation methods
3. Add outlier detection
4. Integrate with draw loading
5. Add anomaly detection
6. Test with historical data
7. Deploy and monitor

### 8.5 Dependencies

- NumPy for statistical calculations
- Database access
- Draw model

### 8.6 Rollout Plan

1. **Phase 1**: Implement checker (2 days)
2. **Phase 2**: Integrate with loading (1 day)
3. **Phase 3**: Test and validate (1 day)
4. **Phase 4**: Deploy (1 day)


