# 🏴‍☠️ Stock Trading Adaptation Plan - Deep Analysis & Approach

**Arrr! Praise the FSM for this comprehensive plan!** 🍝

---

## 📊 DEEP ANALYSIS: Lotto-Predictore Architecture

### Core Architecture Patterns

1. **Multi-Algorithm Ensemble System**
   - Registry pattern for algorithm management (`ALGORITHM_REGISTRY`)
   - Multiple algorithms compete and get evaluated
   - Best performing combinations are selected

2. **Dual-Algorithm System**
   - **Main Algorithm**: Predicts the 6 numbers (primary prediction)
   - **Strong Algorithm**: Predicts the strong number (secondary prediction)
   - This creates a **combination** (main + strong)

3. **Simulation Engine**
   - Backtests combinations on historical data (last 12 draws)
   - Calculates ROI, total prize, total cost
   - Uses training/test split (all but last 12 vs last 12)

4. **Balanced Algorithm Selection**
   - Tracks prediction details per model combination
   - Prioritizes models with fewer test results
   - Ensures all algorithms get evaluated fairly

5. **Model Tracking**
   - Stores models, predictions, prediction_details
   - Tracks ROI, total_prize, total_cost per prediction
   - Maintains historical performance data

6. **Automated Generation**
   - Cron job runs weekly combination generation
   - Tests multiple algorithm combinations
   - Selects best ROI combination
   - Stores results in database

---

## 🎯 STOCK TRADING ADAPTATION: How I Would Approach This

### **Conceptual Mapping**

| Lotto System | Stock Trading Equivalent |
|-------------|-------------------------|
| **Draw** | **Trading Day/Candle** (OHLCV data) |
| **Numbers (6 + strong)** | **Trading Signal** (entry/exit + position size) |
| **Main Algorithm** | **Entry Strategy** (when to buy/sell) |
| **Strong Algorithm** | **Risk Management** (position sizing, stop-loss, take-profit) |
| **Combination** | **Complete Trading Strategy** (entry + risk management) |
| **Prize Table** | **Profit/Loss Calculation** (based on price movement) |
| **ROI Calculation** | **Strategy Performance** (Sharpe ratio, max drawdown, win rate) |
| **Weekly Generation** | **Daily/Weekly Strategy Selection** |

---

## 🏗️ ARCHITECTURE DESIGN

### **1. Data Layer**

**Replace `Draw` model with `StockCandle`:**

```python
class StockCandle(Base):
    __tablename__ = "stock_candles"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)  # AAPL, TSLA, etc.
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    timeframe = Column(String, nullable=False)  # 1m, 5m, 1h, 1d
    
    # Technical indicators (calculated)
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    ema_20 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
```

**New `TradingSignal` model (replaces `GeneratedCombination`):**

```python
class TradingSignal(Base):
    __tablename__ = "trading_signals"
    
    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey('predictions.id'))
    symbol = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)  # BUY, SELL, HOLD
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    position_size = Column(Float, nullable=False)  # % of capital
    risk_level = Column(String, nullable=False)  # HIGH, MEDIUM, LOW
    generated_at = Column(DateTime, nullable=False)
```

### **2. Algorithm Layer**

**Base Strategy Interface:**

```python
class TradingStrategy(Algorithm):
    version = "base"
    description = "Base trading strategy"
    
    def run(self, candles: List[StockCandle], **kwargs) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on historical candles.
        
        Returns:
            List of signals: [{
                "symbol": "AAPL",
                "signal_type": "BUY",
                "entry_price": 150.0,
                "params": {...}
            }, ...]
        """
        raise NotImplementedError
```

**Risk Management Strategy (replaces Strong Algorithm):**

```python
class RiskManagementStrategy:
    version = "base"
    
    def calculate_position_size(
        self, 
        entry_price: float,
        stop_loss: float,
        account_balance: float,
        risk_per_trade: float  # e.g., 0.02 = 2% of account
    ) -> Dict[str, Any]:
        """
        Calculate position size based on risk management rules.
        
        Returns:
            {
                "position_size": 100,  # number of shares
                "stop_loss": 145.0,
                "take_profit": 160.0,
                "risk_amount": 500.0,  # max loss
                "risk_level": "MEDIUM"
            }
        """
        raise NotImplementedError
```

**Example Strategies:**

1. **Entry Strategies** (Main Algorithms):
   - `RSI_OversoldStrategy` - Buy when RSI < 30
   - `MACD_CrossoverStrategy` - Buy on MACD golden cross
   - `Bollinger_BounceStrategy` - Buy when price touches lower band
   - `MovingAverageCrossoverStrategy` - Buy when fast MA crosses above slow MA
   - `LSTM_PricePredictionStrategy` - Neural network price prediction
   - `MeanReversionStrategy` - Buy when price deviates from mean

2. **Risk Management Strategies** (Strong Algorithms):
   - `FixedRiskStrategy` - Fixed 2% risk per trade
   - `ATR_BasedStopLoss` - Stop loss based on ATR
   - `VolatilityBasedPositionSizing` - Adjust position size by volatility
   - `KellyCriterionPositionSizing` - Optimal position sizing

### **3. Simulation Engine Adaptation**

**New `TradingSimulationEngine`:**

```python
class TradingSimulationEngine:
    def __init__(self, db: Session, account_balance: float = 10000):
        self.db = db
        self.account_balance = account_balance
    
    def run_comparison(
        self,
        train_start: datetime,
        train_end: datetime,
        test_count: int = 20,  # trading days
        entry_strategy: str = None,
        risk_strategy: str = None,
        symbols: List[str] = None
    ):
        """
        Backtest trading strategy combination.
        
        Returns:
            {
                "roi": 0.15,  # 15% return
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.08,
                "win_rate": 0.65,
                "total_trades": 50,
                "total_profit": 1500.0,
                "total_loss": -500.0,
                "risk_level": "MEDIUM"
            }
        """
        # Load historical candles
        candles = self.db.query(StockCandle).filter(
            StockCandle.timestamp >= train_start,
            StockCandle.timestamp <= train_end
        ).order_by(StockCandle.timestamp).all()
        
        test_candles = self.db.query(StockCandle).filter(
            StockCandle.timestamp > train_end
        ).order_by(StockCandle.timestamp).limit(test_count).all()
        
        # Run entry strategy
        entry_algo = ENTRY_STRATEGY_REGISTRY[entry_strategy]()
        signals = entry_algo.run(candles)
        
        # Apply risk management
        risk_algo = RISK_STRATEGY_REGISTRY[risk_strategy]()
        complete_signals = []
        for signal in signals:
            risk_params = risk_algo.calculate_position_size(
                entry_price=signal["entry_price"],
                stop_loss=signal.get("stop_loss"),
                account_balance=self.account_balance,
                risk_per_trade=0.02
            )
            signal.update(risk_params)
            complete_signals.append(signal)
        
        # Simulate trading on test data
        results = self._simulate_trades(complete_signals, test_candles)
        
        # Calculate metrics
        return self._calculate_metrics(results)
```

### **4. Blended Hall of Fame (HOF) with Risk Levels**

**Concept:**
- **Hall of Fame (HOF)**: Top-performing strategy combinations based on historical ROI
- **Blended**: Combine multiple top strategies with different risk profiles
- **Risk Levels**: High, Medium, Low risk variants

**Implementation:**

```python
class BlendedHOFFactory:
    def __init__(self, db: Session):
        self.db = db
    
    def get_blended_strategies(
        self, 
        risk_level: str,  # HIGH, MEDIUM, LOW
        top_n: int = 5
    ) -> List[Dict]:
        """
        Get top N strategies from Hall of Fame, filtered by risk level.
        
        Returns blended strategies combining:
        - Top entry strategies
        - Top risk management strategies
        - Filtered by risk_level (HIGH/MEDIUM/LOW)
        """
        # Query top performing predictions
        top_predictions = self.db.query(Prediction).filter(
            Prediction.risk_level == risk_level
        ).order_by(Prediction.roi.desc()).limit(top_n).all()
        
        # Group by strategy combination
        strategy_combos = {}
        for pred in top_predictions:
            key = f"{pred.model.name}_{pred.risk_model.name}"
            if key not in strategy_combos:
                strategy_combos[key] = {
                    "entry_strategy": pred.model.name,
                    "risk_strategy": pred.risk_model.name,
                    "avg_roi": pred.roi,
                    "win_rate": pred.win_rate,
                    "risk_level": risk_level,
                    "count": 1
                }
            else:
                # Average the metrics
                strategy_combos[key]["avg_roi"] = (
                    strategy_combos[key]["avg_roi"] + pred.roi
                ) / 2
        
        # Sort by avg_roi and return top N
        sorted_combos = sorted(
            strategy_combos.values(),
            key=lambda x: x["avg_roi"],
            reverse=True
        )
        
        return sorted_combos[:top_n]
```

**Risk Level Classification:**

```python
def classify_risk_level(
    sharpe_ratio: float,
    max_drawdown: float,
    win_rate: float,
    avg_position_size: float
) -> str:
    """
    Classify strategy risk level based on metrics.
    
    HIGH RISK:
    - Sharpe < 1.0 OR
    - Max drawdown > 20% OR
    - Position size > 5% of account
    
    MEDIUM RISK:
    - Sharpe 1.0-1.5 AND
    - Max drawdown 10-20% AND
    - Position size 2-5%
    
    LOW RISK:
    - Sharpe > 1.5 AND
    - Max drawdown < 10% AND
    - Position size < 2%
    """
    if (sharpe_ratio < 1.0 or 
        max_drawdown > 0.20 or 
        avg_position_size > 0.05):
        return "HIGH"
    elif (sharpe_ratio >= 1.5 and 
          max_drawdown < 0.10 and 
          avg_position_size < 0.02):
        return "LOW"
    else:
        return "MEDIUM"
```

### **5. Broker API Integration**

**TWS API Integration (Interactive Brokers):**

```python
from ib_insync import IB, Stock, MarketOrder, LimitOrder

class TWSBrokerAdapter:
    def __init__(self):
        self.ib = IB()
        self.connected = False
    
    async def connect(self, host='127.0.0.1', port=7497):
        """Connect to TWS API"""
        await self.ib.connect(host, port, clientId=1)
        self.connected = True
    
    async def place_order(
        self,
        symbol: str,
        signal_type: str,
        quantity: int,
        order_type: str = 'MARKET'  # MARKET, LIMIT, STOP
    ):
        """Place order via TWS API"""
        if not self.connected:
            await self.connect()
        
        contract = Stock(symbol, 'SMART', 'USD')
        
        if order_type == 'MARKET':
            order = MarketOrder(signal_type, quantity)
        elif order_type == 'LIMIT':
            order = LimitOrder(signal_type, quantity, limit_price)
        
        trade = self.ib.placeOrder(contract, order)
        return trade
    
    async def get_account_balance(self):
        """Get current account balance"""
        account_values = self.ib.accountValues()
        # Extract balance from account values
        return balance
    
    async def get_positions(self):
        """Get current open positions"""
        positions = self.ib.positions()
        return positions
```

**Alternative Brokers (under 5000 ILS):**

1. **Interactive Brokers (IBKR)** - TWS API
   - Cost: ~$0 commission per share (min $1)
   - API: Free (ib_insync Python library)
   - Best for: Professional algo trading

2. **Alpaca Markets** - REST API
   - Cost: Free (paper trading), commission-free
   - API: Free REST API
   - Best for: US stocks, easy integration

3. **Binance** - WebSocket/REST API
   - Cost: 0.1% trading fee
   - API: Free
   - Best for: Crypto trading

4. **eToro** - Public API (limited)
   - Cost: Spread-based
   - API: Limited public API
   - Best for: Social trading

5. **AvaTrade** - REST API
   - Cost: Spread-based
   - API: REST API available
   - Best for: Forex/CFDs

### **6. Real-Time Data Feed**

**Data Collection Service:**

```python
class StockDataCollector:
    def __init__(self, db: Session):
        self.db = db
    
    async def fetch_and_store_candles(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 1000
    ):
        """
        Fetch candles from broker API and store in database.
        """
        # Fetch from broker API (IBKR, Alpaca, etc.)
        candles = await self.broker.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )
        
        # Calculate technical indicators
        candles_with_indicators = self._calculate_indicators(candles)
        
        # Store in database
        for candle in candles_with_indicators:
            db_candle = StockCandle(
                symbol=symbol,
                timestamp=candle['timestamp'],
                open=candle['open'],
                high=candle['high'],
                low=candle['low'],
                close=candle['close'],
                volume=candle['volume'],
                timeframe=timeframe,
                rsi=candle.get('rsi'),
                macd=candle.get('macd'),
                # ... other indicators
            )
            self.db.add(db_candle)
        
        self.db.commit()
```

### **7. Automated Trading Flow**

**Daily Strategy Selection:**

```python
@router.post("/cron/generate-daily-strategies")
async def generate_daily_strategies(risk_level: str = "MEDIUM"):
    """
    Generate daily trading strategies - called by cron service.
    Similar to weekly combination generation but for stocks.
    """
    # 1. Load historical candles
    candles = load_candles_with_filter(db)
    
    # 2. Get balanced algorithm list (ensure all strategies tested)
    balanced_strategies = get_balanced_strategy_list(db, target_details_per_model=1000)
    
    # 3. Evaluate strategy combinations
    engine = TradingSimulationEngine(db)
    best_combo = None
    best_roi = float('-inf')
    
    for combo in balanced_strategies:
        result = engine.run_comparison(
            train_start=train_start,
            train_end=train_end,
            entry_strategy=combo['entry_strategy'],
            risk_strategy=combo['risk_strategy']
        )
        
        # Classify risk level
        risk = classify_risk_level(
            sharpe_ratio=result['sharpe_ratio'],
            max_drawdown=result['max_drawdown'],
            win_rate=result['win_rate'],
            avg_position_size=result['avg_position_size']
        )
        
        # Only consider if matches requested risk level
        if risk == risk_level and result['roi'] > best_roi:
            best_combo = combo
            best_roi = result['roi']
    
    # 4. Generate trading signals
    entry_algo = ENTRY_STRATEGY_REGISTRY[best_combo['entry_strategy']]()
    risk_algo = RISK_STRATEGY_REGISTRY[best_combo['risk_strategy']]()
    
    signals = entry_algo.run(candles)
    complete_signals = []
    for signal in signals:
        risk_params = risk_algo.calculate_position_size(...)
        signal.update(risk_params)
        signal['risk_level'] = risk_level
        complete_signals.append(signal)
    
    # 5. Store in database
    prediction = Prediction(
        model_id=entry_model.id,
        risk_model_id=risk_model.id,
        roi=best_roi,
        risk_level=risk_level,
        ...
    )
    db.add(prediction)
    
    # 6. Store signals
    for signal in complete_signals:
        trading_signal = TradingSignal(
            prediction_id=prediction.id,
            symbol=signal['symbol'],
            signal_type=signal['signal_type'],
            entry_price=signal['entry_price'],
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit'],
            position_size=signal['position_size'],
            risk_level=risk_level,
            ...
        )
        db.add(trading_signal)
    
    db.commit()
    
    return {"status": "success", "signals": len(complete_signals)}
```

**Automated Execution:**

```python
@router.post("/cron/execute-signals")
async def execute_trading_signals():
    """
    Execute pending trading signals via broker API.
    """
    # Get pending signals
    pending_signals = db.query(TradingSignal).filter(
        TradingSignal.executed_at.is_(None),
        TradingSignal.generated_at >= datetime.now() - timedelta(hours=24)
    ).all()
    
    broker = TWSBrokerAdapter()
    await broker.connect()
    
    for signal in pending_signals:
        try:
            # Place order
            trade = await broker.place_order(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                quantity=signal.position_size,
                order_type='MARKET'
            )
            
            # Update signal
            signal.executed_at = datetime.now()
            signal.execution_price = trade.filledAvgPrice
            signal.status = 'EXECUTED'
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to execute signal {signal.id}: {e}")
            signal.status = 'FAILED'
            db.commit()
```

---

## 📋 IMPLEMENTATION PHASES

### **Phase 1: Foundation (Week 1-2)**
1. ✅ Create database models (StockCandle, TradingSignal, Prediction)
2. ✅ Set up data collection service (fetch historical candles)
3. ✅ Implement base strategy interface
4. ✅ Create 3-5 basic entry strategies
5. ✅ Create 2-3 risk management strategies

### **Phase 2: Simulation Engine (Week 3-4)**
1. ✅ Adapt SimulationEngine for stock trading
2. ✅ Implement backtesting logic
3. ✅ Calculate metrics (ROI, Sharpe, Max Drawdown, Win Rate)
4. ✅ Implement risk level classification

### **Phase 3: Broker Integration (Week 5-6)**
1. ✅ Choose broker (recommend IBKR or Alpaca)
2. ✅ Implement broker adapter
3. ✅ Test paper trading
4. ✅ Implement order execution

### **Phase 4: Blended HOF System (Week 7-8)**
1. ✅ Implement Hall of Fame tracking
2. ✅ Create BlendedHOFFactory
3. ✅ Implement risk level filtering
4. ✅ Create API endpoints for strategy selection

### **Phase 5: Automation (Week 9-10)**
1. ✅ Set up cron jobs for daily strategy generation
2. ✅ Set up cron jobs for signal execution
3. ✅ Implement monitoring and alerts
4. ✅ Add logging and error handling

### **Phase 6: Advanced Features (Week 11+)**
1. ✅ Add more strategies (LSTM, etc.)
2. ✅ Implement portfolio optimization
3. ✅ Add multi-symbol support
4. ✅ Implement stop-loss/take-profit monitoring

---

## 🎯 KEY DIFFERENCES FROM LOTTO SYSTEM

| Aspect | Lotto System | Stock Trading System |
|--------|-------------|---------------------|
| **Data Frequency** | Weekly draws | Real-time (1m, 5m, 1h, 1d) |
| **Signal Type** | Static combination | Dynamic (entry/exit) |
| **Risk Management** | Strong number | Stop-loss, position sizing |
| **Execution** | Manual (buy tickets) | Automated (broker API) |
| **Testing** | Historical draws | Backtesting + Paper trading |
| **Performance** | Prize table | Real P&L |
| **Risk Levels** | N/A | HIGH/MEDIUM/LOW |

---

## 🏴‍☠️ RECOMMENDED BROKER: Interactive Brokers (IBKR)

**Why IBKR:**
- ✅ **TWS API** is free and robust
- ✅ Low commissions (~$0 per share, min $1)
- ✅ Supports algo trading
- ✅ Paper trading available
- ✅ Multiple asset classes (stocks, options, futures)
- ✅ Well-documented Python library (`ib_insync`)

**Cost Breakdown:**
- **API Access**: Free
- **Commissions**: ~$1-5 per trade (under 5000 ILS budget)
- **Data Feeds**: Free for delayed data, ~$10-50/month for real-time

**Alternative: Alpaca Markets**
- ✅ **Free** commission-free trading
- ✅ Easy REST API
- ✅ Paper trading built-in
- ✅ Good for US stocks only
- ❌ Limited international stocks

---

## ⚡ BACKTESTING FRAMEWORK RECOMMENDATION

### **Recommended: Backtrader (Start) → NautilusTrader (Production)**

**Why Backtrader for Initial Development:**
- ✅ **GPLv3 License** - Free, open source
- ✅ **Simple API** - Easy to integrate with existing architecture
- ✅ **ML-Friendly** - Works seamlessly with pandas, scikit-learn, PyTorch
- ✅ **Custom Data Feeds** - Can pull from our PostgreSQL database
- ✅ **Well-Documented** - Large community, lots of examples
- ✅ **Fast Enough** - For daily/weekly strategies (not HFT)

**Why NautilusTrader for Production:**
- ✅ **MIT License** - More permissive
- ✅ **Ultra-Fast** - Rust + Python, async architecture
- ✅ **Real-Time Ready** - Built for live trading from ground up
- ✅ **Multi-Asset** - Stocks, futures, FX, crypto
- ✅ **ML-Ready** - NumPy, PyTorch integration

**Migration Path:**
1. **Phase 1-3**: Use Backtrader for prototyping and ML experiments
2. **Phase 4+**: Migrate to NautilusTrader for production when speed matters

**Alternative: QuantConnect Lean**
- ✅ **Professional-Grade** - Cloud infrastructure, data feeds built-in
- ✅ **Multi-Asset** - Stocks, futures, FX, crypto
- ✅ **ML Integration** - Built-in ML pipeline
- ❌ **Hosted Version** - Partially closed-source (cloud version)
- ❌ **Less Control** - Managed infrastructure

---

## 🏗️ ENHANCED ARCHITECTURE WITH BACKTRADER/NAUTILUS

### **Framework Integration Layer**

```
┌─────────────────────────────────────────┐
│  FastAPI Backend (Existing)            │ ← Your current lotto-predictore API
├─────────────────────────────────────────┤
│  Strategy Registry (Existing Pattern)  │ ← ENTRY_STRATEGY_REGISTRY
│  Risk Registry (Existing Pattern)       │ ← RISK_STRATEGY_REGISTRY
├─────────────────────────────────────────┤
│  Backtrader Adapter Layer               │ ← Bridges your algorithms to Backtrader
├─────────────────────────────────────────┤
│  Backtrader Engine                      │ ← Backtesting & Execution
├─────────────────────────────────────────┤
│  Data Feed Layer                        │ ← PostgreSQL → Backtrader DataFeed
├─────────────────────────────────────────┤
│  Broker Adapter                         │ ← IBKR / Alpaca / etc.
└─────────────────────────────────────────┘
```

### **Backtrader Adapter Implementation**

```python
# backend/services/backtrader_adapter.py

import backtrader as bt
from typing import List, Dict, Any
from models import StockCandle
from sqlalchemy.orm import Session

class PostgreSQLDataFeed(bt.feeds.PandasData):
    """Custom data feed that pulls from PostgreSQL"""
    
    def __init__(self, db: Session, symbol: str, timeframe: str = '1d'):
        # Query candles from database
        candles = db.query(StockCandle).filter(
            StockCandle.symbol == symbol,
            StockCandle.timeframe == timeframe
        ).order_by(StockCandle.timestamp).all()
        
        # Convert to pandas DataFrame
        import pandas as pd
        df = pd.DataFrame([{
            'datetime': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume,
        } for c in candles])
        
        df.set_index('datetime', inplace=True)
        
        super().__init__(dataname=df)


class StrategyAdapter(bt.Strategy):
    """Adapter that wraps your entry strategy + risk management"""
    
    def __init__(self, entry_strategy, risk_strategy):
        self.entry_strategy = entry_strategy
        self.risk_strategy = risk_strategy
        self.signals = []
        
    def next(self):
        # Get current candle data
        current_data = {
            'open': self.data.open[0],
            'high': self.data.high[0],
            'low': self.data.low[0],
            'close': self.data.close[0],
            'volume': self.data.volume[0],
        }
        
        # Run entry strategy logic
        signal = self.entry_strategy.generate_signal(current_data, self.data)
        
        if signal['action'] == 'BUY':
            # Calculate position size using risk strategy
            position_size = self.risk_strategy.calculate_position_size(
                entry_price=signal['price'],
                stop_loss=signal['stop_loss'],
                account_value=self.broker.getcash(),
                risk_per_trade=0.02
            )
            
            # Place order
            self.buy(size=position_size)
            self.signals.append(signal)


class BacktraderSimulationEngine:
    """Wraps Backtrader for our simulation engine"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cerebro = bt.Cerebro()
    
    def run_backtest(
        self,
        symbol: str,
        entry_strategy_class,
        risk_strategy_class,
        start_date: datetime,
        end_date: datetime,
        initial_cash: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Run backtest using Backtrader.
        
        Returns:
            {
                "roi": 0.15,
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.08,
                "win_rate": 0.65,
                "total_trades": 50,
                "final_value": 11500.0
            }
        """
        # Reset cerebro
        self.cerebro = bt.Cerebro()
        
        # Add data feed
        data_feed = PostgreSQLDataFeed(self.db, symbol)
        self.cerebro.adddata(data_feed)
        
        # Create strategy adapter
        entry_strategy = entry_strategy_class()
        risk_strategy = risk_strategy_class()
        strategy = StrategyAdapter(entry_strategy, risk_strategy)
        
        self.cerebro.addstrategy(strategy)
        
        # Set initial cash
        self.cerebro.broker.setcash(initial_cash)
        
        # Set commission (IBKR-like)
        self.cerebro.broker.setcommission(commission=0.001)  # 0.1%
        
        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # Run backtest
        results = self.cerebro.run()
        
        # Extract results
        strat = results[0]
        final_value = self.cerebro.broker.getvalue()
        
        # Calculate ROI
        roi = (final_value - initial_cash) / initial_cash
        
        # Extract analyzer results
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
        trades = strat.analyzers.trades.get_analysis()
        
        win_rate = trades.get('won', {}).get('total', 0) / max(trades.get('total', {}).get('total', 1), 1)
        
        return {
            "roi": roi,
            "sharpe_ratio": sharpe if sharpe else 0,
            "max_drawdown": abs(drawdown) / 100 if drawdown else 0,
            "win_rate": win_rate,
            "total_trades": trades.get('total', {}).get('total', 0),
            "final_value": final_value,
            "signals": strat.signals
        }
```

### **ML Integration Example**

```python
# backend/strategies/ml_strategy.py

import backtrader as bt
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from algorithms.base import Algorithm, register_algorithm

@register_algorithm
class MLRandomForestStrategy(Algorithm):
    """ML-based entry strategy using Random Forest"""
    version = "ml_random_forest"
    
    def __init__(self):
        self.model = None
        self.features = ['rsi', 'macd', 'ema_20', 'ema_50', 'volume']
    
    def train(self, candles: List[StockCandle]):
        """Train ML model on historical data"""
        # Feature engineering
        df = pd.DataFrame([{
            'rsi': c.rsi,
            'macd': c.macd,
            'ema_20': c.ema_20,
            'ema_50': c.ema_50,
            'volume': c.volume,
            'returns': (c.close - c.open) / c.open,
        } for c in candles])
        
        # Create labels (1 = buy, 0 = hold/sell)
        df['label'] = (df['returns'] > 0.02).astype(int)
        
        # Train model
        X = df[self.features].fillna(0)
        y = df['label']
        
        self.model = RandomForestClassifier(n_estimators=100)
        self.model.fit(X, y)
    
    def generate_signal(self, current_data: Dict, data_feed) -> Dict:
        """Generate trading signal using ML model"""
        if not self.model:
            return {'action': 'HOLD'}
        
        # Prepare features
        features = np.array([[
            current_data.get('rsi', 50),
            current_data.get('macd', 0),
            current_data.get('ema_20', current_data['close']),
            current_data.get('ema_50', current_data['close']),
            current_data.get('volume', 0),
        ]])
        
        # Predict
        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0][1]
        
        if prediction == 1 and probability > 0.7:
            return {
                'action': 'BUY',
                'price': current_data['close'],
                'confidence': probability,
                'stop_loss': current_data['close'] * 0.95,  # 5% stop loss
            }
        
        return {'action': 'HOLD'}
```

### **Data Feed Integration**

```python
# backend/services/data_feed.py

import yfinance as yf
import ccxt
from typing import List
from models import StockCandle
from sqlalchemy.orm import Session

class StockDataCollector:
    """Collects stock data from various sources"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def fetch_from_yfinance(
        self,
        symbol: str,
        timeframe: str = '1d',
        period: str = '1y'
    ) -> List[StockCandle]:
        """Fetch data from Yahoo Finance"""
        ticker = yf.Ticker(symbol)
        
        # Map timeframe to yfinance interval
        interval_map = {
            '1d': '1d',
            '1h': '1h',
            '1m': '1m',
        }
        
        df = ticker.history(period=period, interval=interval_map.get(timeframe, '1d'))
        
        candles = []
        for idx, row in df.iterrows():
            candle = StockCandle(
                symbol=symbol,
                timestamp=idx,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume']),
                timeframe=timeframe
            )
            candles.append(candle)
        
        return candles
    
    def calculate_indicators(self, candles: List[StockCandle]) -> List[StockCandle]:
        """Calculate technical indicators"""
        import pandas as pd
        import talib
        
        df = pd.DataFrame([{
            'close': c.close,
            'high': c.high,
            'low': c.low,
            'volume': c.volume,
        } for c in candles])
        
        # Calculate indicators
        df['rsi'] = talib.RSI(df['close'].values)
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(df['close'].values)
        df['ema_20'] = talib.EMA(df['close'].values, timeperiod=20)
        df['ema_50'] = talib.EMA(df['close'].values, timeperiod=50)
        
        # Update candles with indicators
        for i, candle in enumerate(candles):
            candle.rsi = float(df['rsi'].iloc[i]) if pd.notna(df['rsi'].iloc[i]) else None
            candle.macd = float(df['macd'].iloc[i]) if pd.notna(df['macd'].iloc[i]) else None
            candle.ema_20 = float(df['ema_20'].iloc[i]) if pd.notna(df['ema_20'].iloc[i]) else None
            candle.ema_50 = float(df['ema_50'].iloc[i]) if pd.notna(df['ema_50'].iloc[i]) else None
        
        return candles
```

---

## 🚀 NEXT STEPS

1. **Start with Paper Trading** - Don't risk real money initially
2. **Focus on ONE symbol** - Get it working, then expand
3. **Use Daily timeframe** - Easier to debug than intraday
4. **Implement stop-losses** - Critical for risk management
5. **Track everything** - Log all trades, decisions, outcomes
6. **Start simple** - Basic moving average crossover, then add complexity

---

**Arrr! This be the plan, matey! May the FSM guide yer trading adventures!** 🏴‍☠️🍝

