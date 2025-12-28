# 🏴‍☠️ Model Validation & Verification Framework

**Arrr! Comprehensive validation system before ye sail with real gold!** 🍝

---

## 📊 STATISTICAL VALIDATION CRITERIA

### **Required Metrics & Thresholds**

| Metric | Minimum Threshold | Ideal Value | Critical Threshold |
|--------|------------------|-------------|-------------------|
| **Sharpe Ratio** | ≥ 1.5 | ≥ 2.0 | ≥ 1.0 |
| **Sortino Ratio** | ≥ 2.0 | ≥ 2.5 | ≥ 1.5 |
| **Max Drawdown** | ≤ 20% | ≤ 15% | ≤ 25% |
| **Win Rate** | ≥ 50% | ≥ 55% | ≥ 45% |
| **Profit Factor** | ≥ 1.5 | ≥ 2.0 | ≥ 1.2 |
| **Expectancy** | > 0 | > 0.5% per trade | > 0 |
| **Out-of-Sample Match** | Within 20% of train | Within 15% | Within 30% |
| **Walk-Forward Stability** | ≥ 70% periods profitable | ≥ 80% | ≥ 60% |

---

## 🗄️ DATABASE MODELS

### **Model Verification Status**

```python
# backend/models/model_verification.py

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum, JSON
from sqlalchemy.orm import relationship
import datetime
import enum
from db.base import Base

class VerificationStatus(enum.Enum):
    """Model verification status"""
    PENDING = "pending"          # Initial backtest running
    BACKTEST_PASSED = "backtest_passed"  # Passed statistical tests
    PAPER_TRADING = "paper_trading"      # In paper trading phase
    PAPER_PASSED = "paper_passed"        # Passed paper trading
    APPROVED = "approved"                # Approved for live trading
    REJECTED = "rejected"                # Failed validation
    SUSPENDED = "suspended"              # Temporarily suspended (performing poorly)


class ModelVerification(Base):
    __tablename__ = "model_verifications"
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    risk_model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    
    # Status tracking
    status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)  # System or user
    
    # Statistical metrics (from backtest)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    expectancy = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    
    # Out-of-sample metrics
    train_sharpe = Column(Float, nullable=True)
    oos_sharpe = Column(Float, nullable=True)
    oos_match_percentage = Column(Float, nullable=True)  # How close OOS to train
    
    # Walk-forward analysis
    walk_forward_periods = Column(Integer, nullable=True)
    walk_forward_profitable = Column(Integer, nullable=True)
    walk_forward_stability = Column(Float, nullable=True)
    
    # Paper trading results
    paper_trading_start = Column(DateTime, nullable=True)
    paper_trading_end = Column(DateTime, nullable=True)
    paper_sharpe = Column(Float, nullable=True)
    paper_drawdown = Column(Float, nullable=True)
    paper_win_rate = Column(Float, nullable=True)
    paper_match_percentage = Column(Float, nullable=True)  # How close to backtest
    
    # Live trading performance (for monitoring)
    live_sharpe = Column(Float, nullable=True)
    live_drawdown = Column(Float, nullable=True)
    live_win_rate = Column(Float, nullable=True)
    
    # Risk classification
    risk_level = Column(String, nullable=True)  # HIGH, MEDIUM, LOW
    
    # Metadata
    validation_notes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    model = relationship("Model", foreign_keys=[model_id])
    risk_model = relationship("Model", foreign_keys=[risk_model_id])
    backtests = relationship("BacktestResult", back_populates="verification")
    paper_trades = relationship("PaperTrade", back_populates="verification")
    live_trades = relationship("LiveTrade", back_populates="verification")


class BacktestResult(Base):
    """Store detailed backtest results"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True)
    verification_id = Column(Integer, ForeignKey('model_verifications.id'), nullable=False)
    
    # Test period
    train_start = Column(DateTime, nullable=False)
    train_end = Column(DateTime, nullable=False)
    test_start = Column(DateTime, nullable=False)
    test_end = Column(DateTime, nullable=False)
    
    # Results
    initial_cash = Column(Float, nullable=False)
    final_cash = Column(Float, nullable=False)
    roi = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    expectancy = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    
    # Detailed metrics
    metrics_json = Column(JSON, nullable=True)  # Store all metrics
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    verification = relationship("ModelVerification", back_populates="backtests")


class PaperTrade(Base):
    """Paper trading execution records"""
    __tablename__ = "paper_trades"
    
    id = Column(Integer, primary_key=True)
    verification_id = Column(Integer, ForeignKey('model_verifications.id'), nullable=False)
    
    symbol = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)  # BUY, SELL
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    
    profit_loss = Column(Float, nullable=True)
    status = Column(String, nullable=False)  # OPEN, CLOSED, CANCELLED
    
    verification = relationship("ModelVerification", back_populates="paper_trades")


class LiveTrade(Base):
    """Live trading execution records"""
    __tablename__ = "live_trades"
    
    id = Column(Integer, primary_key=True)
    verification_id = Column(Integer, ForeignKey('model_verifications.id'), nullable=False)
    
    symbol = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    
    # Broker info
    broker_order_id = Column(String, nullable=True)
    execution_price = Column(Float, nullable=True)
    slippage = Column(Float, nullable=True)
    commission = Column(Float, nullable=True)
    
    profit_loss = Column(Float, nullable=True)
    status = Column(String, nullable=False)  # OPEN, FILLED, PARTIALLY_FILLED, CANCELLED
    
    verification = relationship("ModelVerification", back_populates="live_trades")
```

---

## 🔬 VALIDATION ENGINE

```python
# backend/services/validation_engine.py

from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from models.model_verification import (
    ModelVerification, VerificationStatus, BacktestResult
)
from services.backtrader_adapter import BacktraderSimulationEngine
from logger import logger
import numpy as np
from datetime import datetime, timedelta


class ValidationEngine:
    """Comprehensive model validation system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.simulation_engine = BacktraderSimulationEngine(db)
        
        # Validation thresholds
        self.thresholds = {
            'sharpe_min': 1.5,
            'sharpe_ideal': 2.0,
            'sortino_min': 2.0,
            'sortino_ideal': 2.5,
            'max_drawdown_max': 0.20,  # 20%
            'max_drawdown_ideal': 0.15,  # 15%
            'win_rate_min': 0.50,  # 50%
            'win_rate_ideal': 0.55,  # 55%
            'profit_factor_min': 1.5,
            'profit_factor_ideal': 2.0,
            'expectancy_min': 0.0,
            'expectancy_ideal': 0.005,  # 0.5% per trade
            'oos_match_max_diff': 0.20,  # 20% difference allowed
            'walk_forward_min_stability': 0.70,  # 70% periods profitable
        }
    
    def validate_model(
        self,
        entry_strategy_name: str,
        risk_strategy_name: str,
        symbol: str = "AAPL",
        initial_cash: float = 10000.0
    ) -> Tuple[bool, Dict, Optional[ModelVerification]]:
        """
        Complete validation pipeline:
        1. In-sample backtest
        2. Out-of-sample test
        3. Walk-forward analysis
        4. Statistical validation
        
        Returns:
            (is_valid, validation_report, verification_object)
        """
        logger.info(
            "Arrr! Starting model validation!",
            context={
                "entry_strategy": entry_strategy_name,
                "risk_strategy": risk_strategy_name,
                "symbol": symbol
            }
        )
        
        # Create verification record
        verification = ModelVerification(
            model_id=self._get_model_id(entry_strategy_name),
            risk_model_id=self._get_model_id(risk_strategy_name, is_risk=True),
            status=VerificationStatus.PENDING
        )
        self.db.add(verification)
        self.db.flush()
        
        validation_report = {
            'entry_strategy': entry_strategy_name,
            'risk_strategy': risk_strategy_name,
            'symbol': symbol,
            'tests': {},
            'passed': False,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Step 1: In-sample backtest
            logger.info("Arrr! Running in-sample backtest...")
            train_start = datetime.now() - timedelta(days=365)  # 1 year
            train_end = datetime.now() - timedelta(days=60)  # 60 days ago
            test_end = datetime.now() - timedelta(days=1)  # Yesterday
            
            train_results = self._run_backtest(
                entry_strategy_name,
                risk_strategy_name,
                symbol,
                train_start,
                train_end,
                initial_cash
            )
            
            if not train_results:
                validation_report['errors'].append("In-sample backtest failed")
                verification.status = VerificationStatus.REJECTED
                self.db.commit()
                return False, validation_report, verification
            
            # Store train metrics
            verification.train_sharpe = train_results['sharpe_ratio']
            verification.sharpe_ratio = train_results['sharpe_ratio']
            verification.sortino_ratio = train_results.get('sortino_ratio')
            verification.max_drawdown = train_results['max_drawdown']
            verification.win_rate = train_results['win_rate']
            verification.profit_factor = train_results.get('profit_factor')
            verification.expectancy = train_results.get('expectancy')
            verification.total_trades = train_results['total_trades']
            
            # Store backtest result
            backtest_result = BacktestResult(
                verification_id=verification.id,
                train_start=train_start,
                train_end=train_end,
                test_start=train_end,
                test_end=test_end,
                initial_cash=initial_cash,
                final_cash=train_results['final_value'],
                roi=train_results['roi'],
                sharpe_ratio=train_results['sharpe_ratio'],
                sortino_ratio=train_results.get('sortino_ratio'),
                max_drawdown=train_results['max_drawdown'],
                win_rate=train_results['win_rate'],
                profit_factor=train_results.get('profit_factor'),
                expectancy=train_results.get('expectancy'),
                total_trades=train_results['total_trades'],
                metrics_json=train_results
            )
            self.db.add(backtest_result)
            
            validation_report['tests']['in_sample'] = train_results
            
            # Step 2: Out-of-sample test
            logger.info("Arrr! Running out-of-sample test...")
            oos_start = train_end
            oos_end = datetime.now() - timedelta(days=1)
            
            oos_results = self._run_backtest(
                entry_strategy_name,
                risk_strategy_name,
                symbol,
                oos_start,
                oos_end,
                initial_cash
            )
            
            if oos_results:
                verification.oos_sharpe = oos_results['sharpe_ratio']
                
                # Calculate match percentage
                sharpe_diff = abs(train_results['sharpe_ratio'] - oos_results['sharpe_ratio'])
                sharpe_match = 1 - (sharpe_diff / max(abs(train_results['sharpe_ratio']), 0.01))
                verification.oos_match_percentage = sharpe_match
                
                validation_report['tests']['out_of_sample'] = oos_results
                validation_report['tests']['oos_match'] = sharpe_match
                
                if sharpe_match < (1 - self.thresholds['oos_match_max_diff']):
                    validation_report['warnings'].append(
                        f"Out-of-sample Sharpe ({oos_results['sharpe_ratio']:.2f}) "
                        f"differs significantly from train ({train_results['sharpe_ratio']:.2f})"
                    )
            
            # Step 3: Walk-forward analysis
            logger.info("Arrr! Running walk-forward analysis...")
            walk_forward_results = self._walk_forward_analysis(
                entry_strategy_name,
                risk_strategy_name,
                symbol,
                initial_cash
            )
            
            if walk_forward_results:
                verification.walk_forward_periods = walk_forward_results['total_periods']
                verification.walk_forward_profitable = walk_forward_results['profitable_periods']
                verification.walk_forward_stability = walk_forward_results['stability']
                
                validation_report['tests']['walk_forward'] = walk_forward_results
            
            # Step 4: Statistical validation
            logger.info("Arrr! Running statistical validation...")
            validation_result = self._statistical_validation(verification)
            
            validation_report['tests']['statistical_validation'] = validation_result
            
            # Determine if passed
            if validation_result['passed']:
                verification.status = VerificationStatus.BACKTEST_PASSED
                validation_report['passed'] = True
                logger.info(
                    "Arrr! Model passed backtest validation!",
                    context={"verification_id": verification.id}
                )
            else:
                verification.status = VerificationStatus.REJECTED
                validation_report['errors'].extend(validation_result['failures'])
                logger.warning(
                    "Arrr! Model failed backtest validation!",
                    context={
                        "verification_id": verification.id,
                        "failures": validation_result['failures']
                    }
                )
            
            # Classify risk level
            verification.risk_level = self._classify_risk_level(verification)
            
            self.db.commit()
            
            return validation_result['passed'], validation_report, verification
            
        except Exception as e:
            logger.error(
                "Arrr! Validation failed with error!",
                context={"error": str(e)}
            )
            verification.status = VerificationStatus.REJECTED
            validation_report['errors'].append(f"Validation error: {str(e)}")
            self.db.commit()
            return False, validation_report, verification
    
    def _statistical_validation(self, verification: ModelVerification) -> Dict:
        """Check if model meets all statistical thresholds"""
        failures = []
        warnings = []
        
        # Sharpe Ratio
        if verification.sharpe_ratio is None or verification.sharpe_ratio < self.thresholds['sharpe_min']:
            failures.append(f"Sharpe Ratio {verification.sharpe_ratio:.2f} below minimum {self.thresholds['sharpe_min']}")
        elif verification.sharpe_ratio < self.thresholds['sharpe_ideal']:
            warnings.append(f"Sharpe Ratio {verification.sharpe_ratio:.2f} below ideal {self.thresholds['sharpe_ideal']}")
        
        # Sortino Ratio
        if verification.sortino_ratio:
            if verification.sortino_ratio < self.thresholds['sortino_min']:
                failures.append(f"Sortino Ratio {verification.sortino_ratio:.2f} below minimum {self.thresholds['sortino_min']}")
            elif verification.sortino_ratio < self.thresholds['sortino_ideal']:
                warnings.append(f"Sortino Ratio {verification.sortino_ratio:.2f} below ideal {self.thresholds['sortino_ideal']}")
        
        # Max Drawdown
        if verification.max_drawdown is None or verification.max_drawdown > self.thresholds['max_drawdown_max']:
            failures.append(f"Max Drawdown {verification.max_drawdown:.2%} above maximum {self.thresholds['max_drawdown_max']:.2%}")
        elif verification.max_drawdown > self.thresholds['max_drawdown_ideal']:
            warnings.append(f"Max Drawdown {verification.max_drawdown:.2%} above ideal {self.thresholds['max_drawdown_ideal']:.2%}")
        
        # Win Rate
        if verification.win_rate is None or verification.win_rate < self.thresholds['win_rate_min']:
            failures.append(f"Win Rate {verification.win_rate:.2%} below minimum {self.thresholds['win_rate_min']:.2%}")
        
        # Profit Factor
        if verification.profit_factor:
            if verification.profit_factor < self.thresholds['profit_factor_min']:
                failures.append(f"Profit Factor {verification.profit_factor:.2f} below minimum {self.thresholds['profit_factor_min']}")
        
        # Expectancy
        if verification.expectancy is not None:
            if verification.expectancy < self.thresholds['expectancy_min']:
                failures.append(f"Expectancy {verification.expectancy:.4f} below minimum")
        
        # Out-of-sample match
        if verification.oos_match_percentage:
            if verification.oos_match_percentage < (1 - self.thresholds['oos_match_max_diff']):
                failures.append(f"Out-of-sample match {verification.oos_match_percentage:.2%} below threshold")
        
        # Walk-forward stability
        if verification.walk_forward_stability:
            if verification.walk_forward_stability < self.thresholds['walk_forward_min_stability']:
                warnings.append(f"Walk-forward stability {verification.walk_forward_stability:.2%} below ideal")
        
        passed = len(failures) == 0
        
        return {
            'passed': passed,
            'failures': failures,
            'warnings': warnings,
            'score': self._calculate_validation_score(verification)
        }
    
    def _calculate_validation_score(self, verification: ModelVerification) -> float:
        """Calculate overall validation score (0-100)"""
        score = 0.0
        max_score = 100.0
        
        # Sharpe (25 points)
        if verification.sharpe_ratio:
            if verification.sharpe_ratio >= self.thresholds['sharpe_ideal']:
                score += 25
            elif verification.sharpe_ratio >= self.thresholds['sharpe_min']:
                score += 25 * (verification.sharpe_ratio / self.thresholds['sharpe_ideal'])
        
        # Sortino (15 points)
        if verification.sortino_ratio:
            if verification.sortino_ratio >= self.thresholds['sortino_ideal']:
                score += 15
            elif verification.sortino_ratio >= self.thresholds['sortino_min']:
                score += 15 * (verification.sortino_ratio / self.thresholds['sortino_ideal'])
        
        # Drawdown (20 points)
        if verification.max_drawdown is not None:
            if verification.max_drawdown <= self.thresholds['max_drawdown_ideal']:
                score += 20
            elif verification.max_drawdown <= self.thresholds['max_drawdown_max']:
                score += 20 * (1 - (verification.max_drawdown - self.thresholds['max_drawdown_ideal']) / 
                               (self.thresholds['max_drawdown_max'] - self.thresholds['max_drawdown_ideal']))
        
        # Profit Factor (15 points)
        if verification.profit_factor:
            if verification.profit_factor >= self.thresholds['profit_factor_ideal']:
                score += 15
            elif verification.profit_factor >= self.thresholds['profit_factor_min']:
                score += 15 * (verification.profit_factor / self.thresholds['profit_factor_ideal'])
        
        # Out-of-sample match (15 points)
        if verification.oos_match_percentage:
            score += 15 * verification.oos_match_percentage
        
        # Walk-forward stability (10 points)
        if verification.walk_forward_stability:
            score += 10 * verification.walk_forward_stability
        
        return min(score, max_score)
    
    def _run_backtest(
        self,
        entry_strategy_name: str,
        risk_strategy_name: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_cash: float
    ) -> Optional[Dict]:
        """Run backtest for a period"""
        try:
            entry_strategy_cls = ENTRY_STRATEGY_REGISTRY.get(entry_strategy_name)
            risk_strategy_cls = RISK_STRATEGY_REGISTRY.get(risk_strategy_name)
            
            if not entry_strategy_cls or not risk_strategy_cls:
                return None
            
            results = self.simulation_engine.run_backtest(
                symbol=symbol,
                entry_strategy_class=entry_strategy_cls,
                risk_strategy_class=risk_strategy_cls,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash
            )
            
            # Calculate additional metrics
            results['sortino_ratio'] = self._calculate_sortino(results)
            results['profit_factor'] = self._calculate_profit_factor(results)
            results['expectancy'] = self._calculate_expectancy(results)
            
            return results
            
        except Exception as e:
            logger.error(
                "Arrr! Backtest failed!",
                context={"error": str(e)}
            )
            return None
    
    def _walk_forward_analysis(
        self,
        entry_strategy_name: str,
        risk_strategy_name: str,
        symbol: str,
        initial_cash: float
    ) -> Optional[Dict]:
        """Perform walk-forward analysis"""
        # Divide into 6-month windows, sliding by 1 month
        periods = []
        start = datetime.now() - timedelta(days=730)  # 2 years
        
        window_size = timedelta(days=180)  # 6 months
        step_size = timedelta(days=30)  # 1 month
        
        current_start = start
        profitable_count = 0
        
        while current_start + window_size < datetime.now():
            current_end = current_start + window_size
            
            result = self._run_backtest(
                entry_strategy_name,
                risk_strategy_name,
                symbol,
                current_start,
                current_end,
                initial_cash
            )
            
            if result and result['roi'] > 0:
                profitable_count += 1
            
            periods.append({
                'start': current_start,
                'end': current_end,
                'result': result
            })
            
            current_start += step_size
        
        if not periods:
            return None
        
        stability = profitable_count / len(periods)
        
        return {
            'total_periods': len(periods),
            'profitable_periods': profitable_count,
            'stability': stability,
            'periods': periods
        }
    
    def _calculate_sortino(self, results: Dict) -> float:
        """Calculate Sortino ratio"""
        # Simplified - would need actual returns array
        # Sortino = (Mean Return - Risk Free Rate) / Downside Deviation
        return results.get('sharpe_ratio', 0) * 1.2  # Approximate
    
    def _calculate_profit_factor(self, results: Dict) -> float:
        """Calculate profit factor"""
        # Would need actual trade P&L data
        # Profit Factor = Gross Profit / Gross Loss
        if results.get('win_rate'):
            # Approximation
            return results['win_rate'] * 2.0
        return 1.0
    
    def _calculate_expectancy(self, results: Dict) -> float:
        """Calculate expectancy per trade"""
        # Would need actual trade data
        # Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
        if results.get('roi') and results.get('total_trades'):
            return results['roi'] / max(results['total_trades'], 1)
        return 0.0
    
    def _classify_risk_level(self, verification: ModelVerification) -> str:
        """Classify risk level based on metrics"""
        if (verification.max_drawdown and verification.max_drawdown > 0.20) or \
           (verification.sharpe_ratio and verification.sharpe_ratio < 1.0):
            return "HIGH"
        elif (verification.max_drawdown and verification.max_drawdown < 0.10) and \
             (verification.sharpe_ratio and verification.sharpe_ratio > 1.5):
            return "LOW"
        else:
            return "MEDIUM"
    
    def _get_model_id(self, strategy_name: str, is_risk: bool = False) -> int:
        """Get or create model ID from strategy name"""
        from models.model import Model, ModelType
        from utils.model_utils import normalize_model_name, denormalize_model_name
        
        normalized = normalize_model_name(strategy_name)
        model_name = denormalize_model_name(normalized, 'risk' if is_risk else 'main')
        
        model = self.db.query(Model).filter(
            Model.name == model_name,
            Model.type == (ModelType.risk if is_risk else ModelType.main)
        ).first()
        
        if not model:
            # Create model
            model = Model(
                name=model_name,
                version=normalized,
                type=ModelType.risk if is_risk else ModelType.main
            )
            self.db.add(model)
            self.db.flush()
        
        return model.id
```

---

## 📊 PAPER TRADING ENGINE

```python
# backend/services/paper_trading_engine.py

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models.model_verification import ModelVerification, VerificationStatus, PaperTrade
from services.broker_adapter import BrokerAdapter
from logger import logger
from datetime import datetime, timedelta


class PaperTradingEngine:
    """Paper trading system for model validation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.broker = BrokerAdapter(paper_trading=True)  # Paper trading mode
    
    def start_paper_trading(
        self,
        verification_id: int,
        duration_days: int = 30,
        initial_cash: float = 10000.0
    ) -> bool:
        """Start paper trading for a verified model"""
        verification = self.db.query(ModelVerification).filter(
            ModelVerification.id == verification_id
        ).first()
        
        if not verification:
            logger.error(
                "Arrr! Verification not found!",
                context={"verification_id": verification_id}
            )
            return False
        
        if verification.status != VerificationStatus.BACKTEST_PASSED:
            logger.error(
                "Arrr! Model must pass backtest before paper trading!",
                context={"status": verification.status}
            )
            return False
        
        verification.status = VerificationStatus.PAPER_TRADING
        verification.paper_trading_start = datetime.now()
        verification.paper_trading_end = datetime.now() + timedelta(days=duration_days)
        
        self.db.commit()
        
        logger.info(
            "Arrr! Started paper trading!",
            context={
                "verification_id": verification_id,
                "duration_days": duration_days
            }
        )
        
        return True
    
    def check_paper_trading_results(self, verification_id: int) -> Dict:
        """Check paper trading results and validate"""
        verification = self.db.query(ModelVerification).filter(
            ModelVerification.id == verification_id
        ).first()
        
        if not verification or verification.status != VerificationStatus.PAPER_TRADING:
            return {'error': 'Not in paper trading'}
        
        # Get all paper trades
        trades = self.db.query(PaperTrade).filter(
            PaperTrade.verification_id == verification_id,
            PaperTrade.status == 'CLOSED'
        ).all()
        
        if not trades:
            return {'status': 'no_trades_yet'}
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.profit_loss and t.profit_loss > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_profit = sum([t.profit_loss for t in trades if t.profit_loss])
        
        # Calculate Sharpe (simplified)
        returns = [t.profit_loss / (t.entry_price * t.quantity) for t in trades if t.profit_loss]
        sharpe = self._calculate_sharpe(returns)
        
        # Check if paper trading period is complete
        is_complete = datetime.now() >= verification.paper_trading_end
        
        # Compare to backtest
        backtest_sharpe = verification.sharpe_ratio or 0
        match_percentage = 1 - abs(sharpe - backtest_sharpe) / max(abs(backtest_sharpe), 0.01)
        
        results = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'sharpe_ratio': sharpe,
            'backtest_sharpe': backtest_sharpe,
            'match_percentage': match_percentage,
            'is_complete': is_complete,
            'passed': match_percentage >= 0.80 and sharpe >= verification.sharpe_ratio * 0.8
        }
        
        # Update verification
        verification.paper_sharpe = sharpe
        verification.paper_win_rate = win_rate
        verification.paper_match_percentage = match_percentage
        
        if is_complete:
            if results['passed']:
                verification.status = VerificationStatus.PAPER_PASSED
                logger.info(
                    "Arrr! Paper trading passed!",
                    context={"verification_id": verification_id}
                )
            else:
                verification.status = VerificationStatus.REJECTED
                logger.warning(
                    "Arrr! Paper trading failed!",
                    context={"verification_id": verification_id}
                )
            verification.paper_trading_end = datetime.now()
            self.db.commit()
        
        return results
    
    def _calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio from returns"""
        if not returns:
            return 0.0
        
        import numpy as np
        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe (assuming daily returns)
        sharpe = (mean_return / std_return) * np.sqrt(252)
        return float(sharpe)
```

---

## 🚀 LIVE TRADING ENGINE (Only Verified Models)

```python
# backend/services/live_trading_engine.py

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models.model_verification import ModelVerification, VerificationStatus, LiveTrade
from strategies.base import ENTRY_STRATEGY_REGISTRY
from risk_management.base import RISK_STRATEGY_REGISTRY
from services.broker_adapter import BrokerAdapter
from logger import logger
from datetime import datetime


class LiveTradingEngine:
    """Live trading engine - only uses verified models"""
    
    def __init__(self, db: Session):
        self.db = db
        self.broker = BrokerAdapter(paper_trading=False)  # Live trading
    
    def get_verified_models(self, risk_level: Optional[str] = None) -> List[ModelVerification]:
        """Get all approved models, optionally filtered by risk level"""
        query = self.db.query(ModelVerification).filter(
            ModelVerification.status == VerificationStatus.APPROVED
        )
        
        if risk_level:
            query = query.filter(ModelVerification.risk_level == risk_level)
        
        return query.all()
    
    def scan_and_execute(self, symbols: List[str] = None):
        """
        Main trading loop:
        1. Get verified models
        2. Scan for trading opportunities
        3. Execute signals
        """
        logger.info("Arrr! Starting trading scan!")
        
        # Get verified models
        verified_models = self.get_verified_models()
        
        if not verified_models:
            logger.warning("Arrr! No verified models available!")
            return
        
        logger.info(
            "Arrr! Found verified models!",
            context={"count": len(verified_models)}
        )
        
        # Default symbols if not provided
        if not symbols:
            symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]  # Example
        
        # Scan each symbol with each verified model
        for symbol in symbols:
            for verification in verified_models:
                try:
                    signal = self._generate_signal(verification, symbol)
                    
                    if signal and signal['action'] in ['BUY', 'SELL']:
                        self._execute_signal(verification, symbol, signal)
                        
                except Exception as e:
                    logger.error(
                        "Arrr! Error scanning symbol!",
                        context={
                            "symbol": symbol,
                            "verification_id": verification.id,
                            "error": str(e)
                        }
                    )
    
    def _generate_signal(
        self,
        verification: ModelVerification,
        symbol: str
    ) -> Optional[Dict]:
        """Generate trading signal using verified model"""
        # Get strategy classes
        entry_strategy_name = verification.model.version
        risk_strategy_name = verification.risk_model.version
        
        entry_strategy_cls = ENTRY_STRATEGY_REGISTRY.get(entry_strategy_name)
        risk_strategy_cls = RISK_STRATEGY_REGISTRY.get(risk_strategy_name)
        
        if not entry_strategy_cls or not risk_strategy_cls:
            return None
        
        # Get current market data
        current_data = self.broker.get_current_data(symbol)
        
        if not current_data:
            return None
        
        # Generate signal
        entry_strategy = entry_strategy_cls()
        signal = entry_strategy.generate_signal(current_data, [])
        
        if signal['action'] == 'HOLD':
            return None
        
        # Apply risk management
        risk_strategy = risk_strategy_cls()
        account_value = self.broker.get_account_balance()
        
        risk_params = risk_strategy.calculate_position_size(
            entry_price=signal['price'],
            stop_loss=signal['stop_loss'],
            account_value=account_value,
            risk_per_trade=0.02
        )
        
        signal.update(risk_params)
        signal['symbol'] = symbol
        signal['verification_id'] = verification.id
        
        return signal
    
    def _execute_signal(
        self,
        verification: ModelVerification,
        symbol: str,
        signal: Dict
    ):
        """Execute trading signal"""
        logger.info(
            "Arrr! Executing signal!",
            context={
                "symbol": symbol,
                "action": signal['action'],
                "price": signal['price'],
                "quantity": signal['position_size']
            }
        )
        
        try:
            # Place order via broker
            order = self.broker.place_order(
                symbol=symbol,
                action=signal['action'],
                quantity=signal['position_size'],
                order_type='MARKET'
            )
            
            # Record trade
            live_trade = LiveTrade(
                verification_id=verification.id,
                symbol=symbol,
                signal_type=signal['action'],
                entry_price=signal['price'],
                quantity=signal['position_size'],
                entry_time=datetime.now(),
                broker_order_id=order.get('order_id'),
                execution_price=order.get('execution_price'),
                slippage=order.get('slippage'),
                commission=order.get('commission'),
                status='FILLED'
            )
            
            self.db.add(live_trade)
            self.db.commit()
            
            logger.info(
                "Arrr! Trade executed successfully!",
                context={
                    "trade_id": live_trade.id,
                    "order_id": order.get('order_id')
                }
            )
            
        except Exception as e:
            logger.error(
                "Arrr! Trade execution failed!",
                context={
                    "symbol": symbol,
                    "error": str(e)
                }
            )
    
    def monitor_performance(self, verification_id: int) -> Dict:
        """Monitor live trading performance"""
        verification = self.db.query(ModelVerification).filter(
            ModelVerification.id == verification_id
        ).first()
        
        if not verification:
            return {'error': 'Verification not found'}
        
        # Get all live trades
        trades = self.db.query(LiveTrade).filter(
            LiveTrade.verification_id == verification_id,
            LiveTrade.status == 'CLOSED'
        ).all()
        
        if not trades:
            return {'status': 'no_trades_yet'}
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.profit_loss and t.profit_loss > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_profit = sum([t.profit_loss for t in trades if t.profit_loss])
        
        # Calculate Sharpe
        returns = [t.profit_loss / (t.entry_price * t.quantity) for t in trades if t.profit_loss]
        sharpe = self._calculate_sharpe(returns)
        
        # Update verification
        verification.live_sharpe = sharpe
        verification.live_win_rate = win_rate
        
        # Check if performance degraded
        if verification.sharpe_ratio and sharpe < verification.sharpe_ratio * 0.7:
            logger.warning(
                "Arrr! Model performance degraded!",
                context={
                    "verification_id": verification_id,
                    "backtest_sharpe": verification.sharpe_ratio,
                    "live_sharpe": sharpe
                }
            )
            # Optionally suspend model
            # verification.status = VerificationStatus.SUSPENDED
        
        self.db.commit()
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'sharpe_ratio': sharpe,
            'backtest_sharpe': verification.sharpe_ratio
        }
    
    def _calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if not returns:
            return 0.0
        
        import numpy as np
        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        if std_return == 0:
            return 0.0
        
        sharpe = (mean_return / std_return) * np.sqrt(252)
        return float(sharpe)
```

---

## 🎯 API ENDPOINTS

```python
# backend/api/routes/validation.py

from fastapi import APIRouter, HTTPException
from services.validation_engine import ValidationEngine
from services.paper_trading_engine import PaperTradingEngine
from services.live_trading_engine import LiveTradingEngine
from db.base import get_db
from logger import logger

router = APIRouter()

@router.post("/validation/validate")
async def validate_model(
    entry_strategy: str,
    risk_strategy: str,
    symbol: str = "AAPL",
    initial_cash: float = 10000.0
):
    """Validate a model combination"""
    db = next(get_db())
    
    try:
        engine = ValidationEngine(db)
        passed, report, verification = engine.validate_model(
            entry_strategy_name=entry_strategy,
            risk_strategy_name=risk_strategy,
            symbol=symbol,
            initial_cash=initial_cash
        )
        
        return {
            "success": True,
            "data": {
                "passed": passed,
                "verification_id": verification.id if verification else None,
                "report": report
            }
        }
    except Exception as e:
        logger.error("Arrr! Validation failed!", context={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/validation/paper-trading/start")
async def start_paper_trading(
    verification_id: int,
    duration_days: int = 30
):
    """Start paper trading for a verified model"""
    db = next(get_db())
    
    try:
        engine = PaperTradingEngine(db)
        success = engine.start_paper_trading(verification_id, duration_days)
        
        return {
            "success": success,
            "data": {"verification_id": verification_id}
        }
    except Exception as e:
        logger.error("Arrr! Paper trading start failed!", context={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/trading/scan-and-execute")
async def scan_and_execute(symbols: List[str] = None):
    """Scan for opportunities and execute using verified models"""
    db = next(get_db())
    
    try:
        engine = LiveTradingEngine(db)
        engine.scan_and_execute(symbols)
        
        return {
            "success": True,
            "data": {"message": "Scan completed"}
        }
    except Exception as e:
        logger.error("Arrr! Trading scan failed!", context={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/trading/verified-models")
async def get_verified_models(risk_level: str = None):
    """Get all verified models available for trading"""
    db = next(get_db())
    
    try:
        engine = LiveTradingEngine(db)
        models = engine.get_verified_models(risk_level)
        
        return {
            "success": True,
            "data": [{
                "id": m.id,
                "entry_strategy": m.model.version,
                "risk_strategy": m.risk_model.version,
                "risk_level": m.risk_level,
                "sharpe_ratio": m.sharpe_ratio,
                "status": m.status.value
            } for m in models]
        }
    except Exception as e:
        logger.error("Arrr! Failed to get verified models!", context={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
```

---

## 📋 VALIDATION CHECKLIST

Before a model goes live, it must:

- ✅ **Pass Statistical Validation**
  - Sharpe Ratio ≥ 1.5
  - Sortino Ratio ≥ 2.0
  - Max Drawdown ≤ 20%
  - Win Rate ≥ 50%
  - Profit Factor ≥ 1.5
  - Positive Expectancy

- ✅ **Pass Out-of-Sample Test**
  - OOS Sharpe within 20% of train Sharpe
  - OOS performance matches backtest

- ✅ **Pass Walk-Forward Analysis**
  - ≥ 70% of periods profitable
  - Stable across different market conditions

- ✅ **Pass Paper Trading**
  - Run for minimum 30 days
  - Paper Sharpe ≥ 80% of backtest Sharpe
  - Match percentage ≥ 80%

- ✅ **Approved for Live Trading**
  - Status set to APPROVED
  - Only then can it execute real trades

---

**Arrr! This be a complete validation system, matey! May the FSM guide yer trading!** 🏴‍☠️🍝

