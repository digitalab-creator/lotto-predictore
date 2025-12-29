# 7. Performance Tracking & Feedback Loop

**Priority: SHOULD HAVE**  
**Impact: Medium-High**  
**Effort: Medium**

## Problem Statement

Currently, there's no automatic system to:
1. **Track Actual Performance**: Compare predictions to actual draw results
2. **Update Metrics**: Automatically update algorithm performance based on real results
3. **Detect Degradation**: Identify when algorithms start underperforming
4. **Trigger Re-optimization**: Automatically re-optimize when performance drops

## Solution Overview

Create automated system that:
- Compares actual draw results to predictions
- Updates algorithm performance metrics automatically
- Detects performance degradation
- Triggers re-optimization when needed
- Generates alerts for significant changes

## Implementation Details

### 7.1 Prediction Validator Service

**File**: `backend/services/core/prediction_validator.py`

```python
class PredictionValidator:
    """
    Validates predictions against actual draw results and updates performance metrics.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.performance_analyzer = PerformanceAnalyzer(db)
    
    def validate_predictions_for_draw(
        self,
        draw_date: date
    ) -> Dict[str, Any]:
        """
        Validate all predictions for a specific draw date.
        Compares predicted combinations to actual draw results.
        """
        # Get actual draw
        actual_draw = self.db.query(Draw).filter(
            Draw.date == draw_date
        ).first()
        
        if not actual_draw:
            return {'error': 'Draw not found'}
        
        # Get all predictions for this date
        predictions = self.db.query(Prediction).join(PredictionDetail).filter(
            PredictionDetail.test_draw_date == draw_date
        ).all()
        
        validation_results = []
        for prediction in predictions:
            details = self.db.query(PredictionDetail).filter(
                PredictionDetail.prediction_id == prediction.id,
                PredictionDetail.test_draw_date == draw_date
            ).all()
            
            for detail in details:
                # Calculate actual performance
                actual_hits = self._calculate_hits(
                    detail.predicted_numbers,
                    actual_draw.numbers
                )
                actual_strong_hit = (
                    detail.predicted_strong == actual_draw.strong_number
                )
                
                # Calculate actual prize and ROI
                actual_prize = calculate_prize(actual_hits, actual_strong_hit)
                actual_roi = (actual_prize - TICKET_COST_PER_TABLE) / TICKET_COST_PER_TABLE
                
                # Update detail record
                detail.actual_hits = actual_hits
                detail.actual_strong_hit = actual_strong_hit
                detail.actual_prize = actual_prize
                detail.actual_roi = actual_roi
                
                validation_results.append({
                    'prediction_id': prediction.id,
                    'detail_id': detail.id,
                    'predicted_hits': detail.hits,
                    'actual_hits': actual_hits,
                    'predicted_roi': detail.roi,
                    'actual_roi': actual_roi,
                    'difference': actual_roi - detail.roi
                })
        
        self.db.commit()
        
        return {
            'draw_date': draw_date,
            'validations': validation_results,
            'total_predictions': len(validation_results)
        }
    
    def update_algorithm_performance(
        self,
        main_algo: str,
        strong_algo: str
    ):
        """
        Update algorithm performance metrics based on latest validations.
        """
        # Get recent performance data
        recent_performance = self.performance_analyzer.analyze_algorithm_performance(
            main_algo, strong_algo, lookback_weeks=4
        )
        
        # Check for degradation
        historical_performance = self.performance_analyzer.analyze_algorithm_performance(
            main_algo, strong_algo, lookback_weeks=12
        )
        
        degradation = self._detect_degradation(
            recent_performance,
            historical_performance
        )
        
        if degradation['significant']:
            logger.warning(
                "Arrr! Algorithm performance degradation detected!",
                context={
                    'main_algo': main_algo,
                    'strong_algo': strong_algo,
                    'recent_roi': recent_performance.get('avg_roi'),
                    'historical_roi': historical_performance.get('avg_roi'),
                    'degradation': degradation
                }
            )
            
            # Trigger re-optimization alert
            self._trigger_reoptimization_alert(main_algo, strong_algo, degradation)
    
    def _detect_degradation(
        self,
        recent: Dict[str, Any],
        historical: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect if algorithm performance is degrading.
        """
        recent_roi = recent.get('avg_roi', 0)
        historical_roi = historical.get('avg_roi', 0)
        
        if historical_roi == 0:
            return {'significant': False}
        
        degradation_pct = (historical_roi - recent_roi) / abs(historical_roi)
        
        return {
            'significant': degradation_pct > 0.20,  # 20% degradation
            'degradation_pct': degradation_pct,
            'recent_roi': recent_roi,
            'historical_roi': historical_roi
        }
    
    def _trigger_reoptimization_alert(
        self,
        main_algo: str,
        strong_algo: str,
        degradation: Dict[str, Any]
    ):
        """
        Trigger alert for re-optimization.
        Could send email, create task, or log critical alert.
        """
        # Log critical alert
        logger.critical(
            "REOPTIMIZATION NEEDED: Algorithm performance degraded",
            context={
                'main_algo': main_algo,
                'strong_algo': strong_algo,
                'degradation': degradation
            }
        )
        
        # Could also:
        # - Send email notification
        # - Create re-optimization task in queue
        # - Update algorithm status in database
```

### 7.2 Automated Validation Cron Job

**File**: `backend/cron/validate_predictions.py`

```python
from services.core.prediction_validator import PredictionValidator
from models import Draw
from db.base import get_db
from logger import logger
from datetime import date, timedelta

def validate_recent_predictions():
    """
    Cron job to validate predictions for recent draws.
    Runs daily after draws are completed.
    """
    db = next(get_db())
    validator = PredictionValidator(db)
    
    try:
        # Get draws from last 7 days that haven't been validated
        cutoff_date = date.today() - timedelta(days=7)
        
        draws = db.query(Draw).filter(
            Draw.date >= cutoff_date,
            Draw.date < date.today()
        ).order_by(Draw.date).all()
        
        for draw in draws:
            logger.info(
                f"Validating predictions for draw {draw.date}",
                context={'draw_date': str(draw.date)}
            )
            
            result = validator.validate_predictions_for_draw(draw.date)
            
            if 'error' not in result:
                logger.info(
                    f"Validated {result['total_predictions']} predictions",
                    context=result
                )
                
                # Update algorithm performance for affected algorithms
                # Get unique algorithm pairs from validated predictions
                # Update each one
                
        logger.info("Arrr! Prediction validation completed, praisin' the FSM!")
        
    except Exception as e:
        logger.error(
            "Arrr! Prediction validation failed!",
            context={'error': str(e)}
        )
    finally:
        db.close()
```

### 7.3 Database Schema Updates

**Add to PredictionDetail**:
```sql
ALTER TABLE prediction_details
ADD COLUMN actual_hits INTEGER,
ADD COLUMN actual_strong_hit BOOLEAN,
ADD COLUMN actual_prize FLOAT,
ADD COLUMN actual_roi FLOAT,
ADD COLUMN validated_at TIMESTAMP;
```

### 7.4 Performance Monitoring Dashboard

**New Endpoint**: `/api/analytics/prediction-performance`

Returns:
- Prediction vs actual performance comparison
- Algorithm performance over time
- Degradation alerts
- Re-optimization recommendations

### 7.5 Expected Outcomes

- **Automatic Updates**: Performance metrics always current
- **Early Detection**: Identify problems before they cause significant losses
- **Data-Driven**: All decisions based on actual performance, not simulations
- **Continuous Improvement**: System automatically adapts

### 7.6 Implementation Steps

1. Create `PredictionValidator` class
2. Add database columns for actual results
3. Create validation cron job
4. Add degradation detection
5. Create monitoring dashboard
6. Add alerting system
7. Test with historical data
8. Deploy and monitor

### 7.7 Dependencies

- Performance analyzer
- Database access
- Cron scheduler
- Logging system

### 7.8 Rollout Plan

1. **Phase 1**: Implement validator (2 days)
2. **Phase 2**: Add database columns (1 day)
3. **Phase 3**: Create cron job (1 day)
4. **Phase 4**: Add monitoring and alerts (2 days)
5. **Phase 5**: Deploy and monitor (ongoing)


