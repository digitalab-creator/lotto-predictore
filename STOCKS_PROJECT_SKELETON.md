# 🏴‍☠️ Stock Trading Project Skeleton

**Arrr! Ready-to-run project structure for stock algo-trading!** 🍝

---

## 📁 PROJECT STRUCTURE

```
stock-trading-backend/
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── strategies.py          # Strategy endpoints
│   │   │   ├── backtest.py           # Backtesting endpoints
│   │   │   ├── signals.py            # Trading signal endpoints
│   │   │   ├── cron/
│   │   │   │   ├── generate_strategies.py  # Daily strategy generation
│   │   │   │   └── execute_signals.py      # Signal execution
│   │   │   └── hof.py                # Hall of Fame endpoints
│   │   └── main.py
│   │
│   ├── strategies/                   # Entry strategies (replaces algorithms/)
│   │   ├── __init__.py
│   │   ├── base.py                   # Base strategy interface
│   │   ├── rsi_strategy.py           # RSI-based entry
│   │   ├── macd_strategy.py          # MACD crossover
│   │   ├── moving_average_strategy.py
│   │   ├── bollinger_strategy.py
│   │   ├── ml_strategy.py            # ML-based strategies
│   │   └── lstm_strategy.py          # LSTM price prediction
│   │
│   ├── risk_management/              # Risk strategies (replaces strong_number/)
│   │   ├── __init__.py
│   │   ├── base.py                   # Base risk management
│   │   ├── fixed_risk.py             # Fixed % risk per trade
│   │   ├── atr_stop_loss.py         # ATR-based stop loss
│   │   ├── volatility_sizing.py     # Volatility-based position sizing
│   │   └── kelly_criterion.py       # Kelly criterion sizing
│   │
│   ├── services/
│   │   ├── backtrader_adapter.py     # Backtrader integration
│   │   ├── simulation_engine.py     # Trading simulation engine
│   │   ├── data_feed.py              # Data collection (yfinance, etc.)
│   │   ├── broker_adapter.py        # IBKR/Alpaca integration
│   │   ├── hof_factory.py           # Hall of Fame strategy selection
│   │   └── risk_classifier.py       # Risk level classification
│   │
│   ├── models/
│   │   ├── stock_candle.py          # OHLCV data
│   │   ├── trading_signal.py        # Trading signals
│   │   ├── prediction.py            # Strategy predictions
│   │   └── model.py                 # Strategy models
│   │
│   ├── db/
│   │   └── base.py
│   │
│   ├── utils/
│   │   ├── technical_indicators.py  # TA-Lib wrapper
│   │   └── metrics.py               # Performance metrics
│   │
│   ├── requirements.txt
│   └── config.py
│
├── docker-compose.yml
├── README.md
└── STOCKS_ADAPTATION_PLAN.md
```

---

## 📦 REQUIREMENTS.TXT (Enhanced)

```txt
# Core Backend
fastapi==0.115.12
uvicorn==0.34.2
sqlalchemy==2.0.41
alembic==1.15.2
psycopg2-binary==2.9.10
pydantic==2.11.4
python-dotenv==1.1.0

# Backtesting Framework
backtrader==1.9.78.123

# Data Collection
yfinance==0.2.32
ccxt==4.1.0
alpaca-trade-api==3.0.0
ib-insync==0.9.86

# Data Processing
pandas==2.1.4
numpy==1.26.2

# Technical Analysis
TA-Lib==0.4.28
finta==1.3
btalib==0.1.3

# Machine Learning
scikit-learn==1.3.2
xgboost==2.0.3
lightgbm==4.1.0
torch==2.3.0

# Visualization
matplotlib==3.8.2
plotly==5.18.0

# Logging
python-json-logger==2.0.7

# Other
requests==2.31.0
backoff==2.2.1
```

---

## 🚀 QUICK START EXAMPLE

### **1. Basic Strategy Example**

```python
# backend/strategies/rsi_strategy.py

from typing import List, Dict, Any
from models import StockCandle
from strategies.base import TradingStrategy, register_strategy

@register_strategy
class RSIStrategy(TradingStrategy):
    version = "rsi_oversold"
    description = "Buy when RSI < 30, sell when RSI > 70"
    
    def __init__(self):
        self.rsi_period = 14
        self.oversold_threshold = 30
        self.overbought_threshold = 70
    
    def generate_signal(
        self, 
        current_data: Dict,
        historical_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate trading signal based on RSI.
        
        Returns:
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'price': float,
                'stop_loss': float,
                'take_profit': float,
                'confidence': float
            }
        """
        current_rsi = current_data.get('rsi')
        
        if not current_rsi:
            return {'action': 'HOLD'}
        
        if current_rsi < self.oversold_threshold:
            return {
                'action': 'BUY',
                'price': current_data['close'],
                'stop_loss': current_data['close'] * 0.95,  # 5% stop loss
                'take_profit': current_data['close'] * 1.10,  # 10% take profit
                'confidence': (self.oversold_threshold - current_rsi) / self.oversold_threshold
            }
        elif current_rsi > self.overbought_threshold:
            return {
                'action': 'SELL',
                'price': current_data['close'],
                'stop_loss': current_data['close'] * 1.05,
                'take_profit': current_data['close'] * 0.90,
                'confidence': (current_rsi - self.overbought_threshold) / (100 - self.overbought_threshold)
            }
        
        return {'action': 'HOLD'}
```

### **2. Risk Management Example**

```python
# backend/risk_management/fixed_risk.py

from typing import Dict
from risk_management.base import RiskManagementStrategy, register_risk_strategy

@register_risk_strategy
class FixedRiskStrategy(RiskManagementStrategy):
    version = "fixed_risk_2pct"
    description = "Fixed 2% risk per trade"
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        account_value: float,
        risk_per_trade: float = 0.02  # 2%
    ) -> Dict[str, Any]:
        """
        Calculate position size based on fixed risk percentage.
        
        Returns:
            {
                'position_size': int,  # number of shares
                'stop_loss': float,
                'take_profit': float,
                'risk_amount': float,
                'risk_level': str
            }
        """
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return {'position_size': 0, 'error': 'Invalid stop loss'}
        
        # Calculate total risk amount
        total_risk = account_value * risk_per_trade
        
        # Calculate position size
        position_size = int(total_risk / risk_per_share)
        
        # Calculate take profit (2:1 risk/reward)
        take_profit = entry_price + (risk_per_share * 2)
        
        # Classify risk level
        risk_level = self._classify_risk(risk_per_trade, position_size, account_value)
        
        return {
            'position_size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_amount': total_risk,
            'risk_level': risk_level
        }
    
    def _classify_risk(self, risk_pct: float, position_size: int, account_value: float) -> str:
        """Classify risk level based on position size"""
        position_value = position_size * account_value * risk_pct
        
        if position_value > account_value * 0.05:  # > 5% of account
            return 'HIGH'
        elif position_value < account_value * 0.02:  # < 2% of account
            return 'LOW'
        else:
            return 'MEDIUM'
```

### **3. Backtest Endpoint Example**

```python
# backend/api/routes/backtest.py

from fastapi import APIRouter, HTTPException
from services.backtrader_adapter import BacktraderSimulationEngine
from strategies.base import ENTRY_STRATEGY_REGISTRY
from risk_management.base import RISK_STRATEGY_REGISTRY
from db.base import get_db
from logger import logger

router = APIRouter()

@router.post("/backtest/run")
async def run_backtest(
    symbol: str,
    entry_strategy: str,
    risk_strategy: str,
    start_date: str,
    end_date: str,
    initial_cash: float = 10000.0
):
    """Run backtest for a strategy combination"""
    
    db = next(get_db())
    
    try:
        # Get strategy classes
        entry_strategy_cls = ENTRY_STRATEGY_REGISTRY.get(entry_strategy)
        risk_strategy_cls = RISK_STRATEGY_REGISTRY.get(risk_strategy)
        
        if not entry_strategy_cls:
            raise HTTPException(status_code=404, detail=f"Entry strategy '{entry_strategy}' not found")
        
        if not risk_strategy_cls:
            raise HTTPException(status_code=404, detail=f"Risk strategy '{risk_strategy}' not found")
        
        # Run backtest
        engine = BacktraderSimulationEngine(db)
        results = engine.run_backtest(
            symbol=symbol,
            entry_strategy_class=entry_strategy_cls,
            risk_strategy_class=risk_strategy_cls,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash
        )
        
        logger.info(
            "Arrr! Backtest completed!",
            context={
                "symbol": symbol,
                "entry_strategy": entry_strategy,
                "risk_strategy": risk_strategy,
                "roi": results["roi"],
                "sharpe_ratio": results["sharpe_ratio"]
            }
        )
        
        return {
            "success": True,
            "data": results
        }
        
    except Exception as e:
        logger.error(
            "Arrr! Backtest failed!",
            context={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
```

---

## 🎯 INTEGRATION WITH EXISTING SYSTEM

### **Strategy Registry Pattern (Same as Lotto)**

```python
# backend/strategies/base.py

from typing import List, Dict, Any

class TradingStrategy:
    version = "base"
    description = "Base trading strategy"
    
    def generate_signal(
        self,
        current_data: Dict,
        historical_data: List[Dict]
    ) -> Dict[str, Any]:
        raise NotImplementedError

# Registry (same pattern as lotto algorithms)
ENTRY_STRATEGY_REGISTRY = {}

def register_strategy(cls):
    ENTRY_STRATEGY_REGISTRY[cls.version] = cls
    return cls
```

### **Simulation Engine Integration**

```python
# backend/services/simulation_engine.py

from services.backtrader_adapter import BacktraderSimulationEngine
from strategies.base import ENTRY_STRATEGY_REGISTRY
from risk_management.base import RISK_STRATEGY_REGISTRY

class TradingSimulationEngine:
    """Wrapper that integrates Backtrader with our system"""
    
    def __init__(self, db):
        self.db = db
        self.backtrader_engine = BacktraderSimulationEngine(db)
    
    def run_comparison(
        self,
        train_start: datetime,
        train_end: datetime,
        test_count: int = 20,
        entry_strategy_names: List[str] = None,
        risk_strategy_names: List[str] = None,
        symbol: str = "AAPL"
    ):
        """Same interface as lotto SimulationEngine"""
        
        results = {}
        
        # Get strategies to test
        entry_strategies = (
            ENTRY_STRATEGY_REGISTRY.items() 
            if not entry_strategy_names 
            else [(name, ENTRY_STRATEGY_REGISTRY[name]) 
                  for name in entry_strategy_names 
                  if name in ENTRY_STRATEGY_REGISTRY]
        )
        
        risk_strategies = (
            RISK_STRATEGY_REGISTRY.items()
            if not risk_strategy_names
            else [(name, RISK_STRATEGY_REGISTRY[name])
                  for name in risk_strategy_names
                  if name in RISK_STRATEGY_REGISTRY]
        )
        
        # Test all combinations
        for entry_name, entry_cls in entry_strategies:
            for risk_name, risk_cls in risk_strategies:
                result = self.backtrader_engine.run_backtest(
                    symbol=symbol,
                    entry_strategy_class=entry_cls,
                    risk_strategy_class=risk_cls,
                    start_date=train_start,
                    end_date=train_end
                )
                
                results[(entry_name, risk_name)] = result
        
        return results
```

---

## 🚀 NEXT STEPS

1. **Copy lotto-predictore structure** → Adapt to stocks
2. **Install Backtrader** → `pip install backtrader`
3. **Create base models** → StockCandle, TradingSignal
4. **Implement 2-3 strategies** → RSI, MACD, Moving Average
5. **Implement 1-2 risk strategies** → Fixed Risk, ATR Stop Loss
6. **Test backtesting** → Run simple backtest
7. **Add ML strategy** → Random Forest or LSTM
8. **Implement HOF system** → Track top strategies by risk level
9. **Add broker integration** → IBKR or Alpaca paper trading
10. **Automate** → Cron jobs for daily generation/execution

---

**Arrr! This skeleton be ready to sail, matey! May the FSM guide yer trading adventures!** 🏴‍☠️🍝

