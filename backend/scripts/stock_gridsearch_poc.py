import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.logger import dh_log
import yfinance as yf
import pandas as pd
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import numpy as np

# 1. Fetch S&P 500 data (SPY ETF)
dh_log("Arrr! Fetchin' SPY data from Yahoo Finance", level="INFO")
data = yf.download("SPY", start="2010-01-01", end="2024-01-01")
if data.empty:
    dh_log("Arrr! Failed to fetch SPY data!", level="ERROR")
    sys.exit(1)
data = data[["Close"]].reset_index()

# 2. Feature engineering: moving averages
data["ma_5"] = data["Close"].rolling(window=5).mean()
data["ma_20"] = data["Close"].rolling(window=20).mean()
data = data.dropna().reset_index(drop=True)

# 3. Train/test split
split = int(len(data) * 0.8)
train, test = data.iloc[:split], data.iloc[split:]

# 4. Prepare X/y for regression (predict next day's close)
X_train = train[["ma_5", "ma_20"]]
y_train = train["Close"].shift(-1).dropna()
X_train = X_train.iloc[:-1]

X_test = test[["ma_5", "ma_20"]]
y_test = test["Close"].shift(-1).dropna()
X_test = X_test.iloc[:-1]

# 5. Grid search on LinearRegression
params = {"fit_intercept": [True, False]}
model = LinearRegression()
tscv = TimeSeriesSplit(n_splits=5)
grid = GridSearchCV(model, params, cv=tscv, scoring="neg_mean_squared_error")
grid.fit(X_train, y_train)
best_model = grid.best_estimator_
dh_log("Arrr! Best model found!", level="INFO", context={"params": grid.best_params_})

# 6. Evaluate on test
dh_log("Arrr! Predictin' on test set", level="INFO")
preds = best_model.predict(X_test)
mse = mean_squared_error(y_test, preds)
dh_log("Arrr! Test MSE calculated!", level="INFO", context={"mse": mse})

# 7. Compare cumulative returns
test = test.iloc[:-1].copy()
test["pred"] = preds
test["pred_return"] = test["pred"].pct_change()
test["spy_return"] = test["Close"].pct_change()
test_cum_pred = (1 + test["pred_return"].fillna(0)).cumprod().iloc[-1]
test_cum_spy = (1 + test["spy_return"].fillna(0)).cumprod().iloc[-1]
dh_log("Arrr! Cumulative returns calculated!", level="INFO", context={
    "model_return": test_cum_pred,
    "spy_return": test_cum_spy
})

print(f"Model return: {test_cum_pred:.4f}")
print(f"SPY return: {test_cum_spy:.4f}")
if test_cum_pred > test_cum_spy:
    print("Arrr! The model be beatin' the market! Praisin' the FSM!")
else:
    print("Arrr! The market still rules the seas... for now!")

# === New: Calculate net profit after half a year with commissions, tax, and monthly deposits ===
start = 10000  # השקעה התחלתית
monthly_deposit = 200  # הפקדה חודשית
commission_rate = 0.001  # 0.1% עמלה בקנייה ובמכירה
tax_rate = 0.25  # מס רווחי הון 25%
period = 0.5  # חצי שנה (אם התשואה היא לשנה)
months = int(6 * period / 0.5)  # חצי שנה = 6 חודשים

# מחשבים את הסכום הסופי עם הפקדות חודשיות (חישוב ריבית דריבית על כל הפקדה)
def calc_final_amount_with_deposits(start, monthly_deposit, ret, commission_rate, tax_rate, months):
    # סכום סופי מהשקעה התחלתית
    commission = start * commission_rate
    total_invested = start
    final = start * ret
    # סכום סופי מהפקדות חודשיות (כל הפקדה צוברת ריבית שונה)
    for m in range(1, months+1):
        months_left = months - m + 1
        # כל הפקדה מושקעת ret^(months_left/months)
        deposit_ret = ret ** (months_left / months)
        final += monthly_deposit * deposit_ret
        commission += monthly_deposit * commission_rate
        total_invested += monthly_deposit
    # עמלת מכירה על כל הסכום
    commission += final * commission_rate
    gross_profit = final - total_invested - commission
    tax = tax_rate * gross_profit if gross_profit > 0 else 0
    net = final - commission - tax
    return {
        'final': net,
        'commission': commission,
        'tax': tax,
        'gross_profit': gross_profit,
        'total_invested': total_invested
    }

model_return_half = test_cum_pred ** period
market_return_half = test_cum_spy ** period

model_stats = calc_final_amount_with_deposits(start, monthly_deposit, model_return_half, commission_rate, tax_rate, 6)
market_stats = calc_final_amount_with_deposits(start, monthly_deposit, market_return_half, commission_rate, tax_rate, 6)

print("\n=== After half a year (net, after tax & commissions, with monthly deposits) ===")
print(f"Model: {model_stats['final']:.2f} ש\"ח (net), profit: {model_stats['gross_profit']:.2f}, tax: {model_stats['tax']:.2f}, commission: {model_stats['commission']:.2f}, invested: {model_stats['total_invested']:.2f}")
print(f"Market: {market_stats['final']:.2f} ש\"ח (net), profit: {market_stats['gross_profit']:.2f}, tax: {market_stats['tax']:.2f}, commission: {market_stats['commission']:.2f}, invested: {market_stats['total_invested']:.2f}")
print(f"Extra profit over market: {model_stats['final'] - market_stats['final']:.2f} ש\"ח")

# === Profit Withdrawal Strategy Simulation ===
def simulate_withdrawals(start, monthly_deposit, annual_return, commission_rate, tax_rate, months, monthly_withdrawal):
    monthly_return = annual_return ** (1/12)
    capital = start
    total_invested = start
    total_withdrawn = 0
    commission = capital * commission_rate
    capital -= commission  # initial buy commission
    
    for m in range(1, months+1):
        # deposit
        capital += monthly_deposit
        total_invested += monthly_deposit
        commission += monthly_deposit * commission_rate
        # monthly return
        capital *= monthly_return
        # profit
        profit = capital - total_invested
        # withdraw from profit only
        withdrawal = min(monthly_withdrawal, profit) if profit > 0 else 0
        capital -= withdrawal
        total_withdrawn += withdrawal
    # sell commission
    commission += capital * commission_rate
    # tax only on remaining profit
    final_profit = capital - total_invested
    tax = tax_rate * final_profit if final_profit > 0 else 0
    final_net = capital - commission - tax
    return {
        'final_net': final_net,
        'total_withdrawn': total_withdrawn,
        'commission': commission,
        'tax': tax,
        'total_invested': total_invested
    }

monthly_withdrawal = 500  # ש"ח לחודש, אם יש רווח
months = 6

model_withdraw = simulate_withdrawals(start, monthly_deposit, model_return_half, commission_rate, tax_rate, months, monthly_withdrawal)
market_withdraw = simulate_withdrawals(start, monthly_deposit, market_return_half, commission_rate, tax_rate, months, monthly_withdrawal)

print("\n=== After half a year WITH monthly profit withdrawals ===")
print(f"Model: withdrawn: {model_withdraw['total_withdrawn']:.2f} ש\"ח, final net: {model_withdraw['final_net']:.2f} ש\"ח, commission: {model_withdraw['commission']:.2f} ש\"ח, tax: {model_withdraw['tax']:.2f} ש\"ח, invested: {model_withdraw['total_invested']:.2f}")
print(f"Market: withdrawn: {market_withdraw['total_withdrawn']:.2f} ש\"ח, final net: {market_withdraw['final_net']:.2f} ש\"ח, commission: {market_withdraw['commission']:.2f} ש\"ח, tax: {market_withdraw['tax']:.2f} ש\"ח, invested: {market_withdraw['total_invested']:.2f}")
print(f"Extra profit over market (withdrawals+final): {(model_withdraw['total_withdrawn'] + model_withdraw['final_net']) - (market_withdraw['total_withdrawn'] + market_withdraw['final_net']):.2f} ש\"ח") 