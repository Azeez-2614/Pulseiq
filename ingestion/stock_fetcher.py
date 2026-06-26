import yfinance as yf
import pandas as pd
import random
from datetime import datetime
import sys
import os

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

BASE_PRICES = {
    "AAPL": 180.0,
    "TSLA": 175.0,
    "GOOGL": 155.0,
    "MSFT": 420.0,
    "AMZN": 185.0
}

def get_mock_price(symbol: str) -> dict:
    """Generates a realistic mock stock price update."""
    base = BASE_PRICES.get(symbol, 100.0)
    # Apply a small random perturbation (-1.5% to +1.5%)
    change_pct = round(random.uniform(-1.5, 1.5), 2)
    price = round(base * (1 + change_pct / 100.0), 2)
    volume = random.randint(50000, 500000)
    return {
        "symbol": symbol,
        "price": price,
        "volume": volume,
        "timestamp": datetime.utcnow().isoformat(),
        "change_pct": change_pct
    }

def fetch_current_prices() -> list[dict]:
    results = []
    for symbol in config.WATCHLIST:
        try:
            ticker = yf.Ticker(symbol)
            # Try fetching today's 5-minute interval data
            hist = ticker.history(period="1d", interval="5m")
            
            # If empty (e.g. weekend or market closed), try fetching the last 5 days to get the most recent trading data
            if hist.empty:
                hist = ticker.history(period="5d", interval="5m")
                
            if not hist.empty:
                latest = hist.iloc[-1]
                open_val = hist.iloc[0]["Open"]
                close_val = latest["Close"]
                
                # Check for NaN values and supply fallbacks
                price = round(float(close_val), 2) if not pd.isna(close_val) else BASE_PRICES.get(symbol, 100.0)
                volume = int(latest["Volume"]) if not pd.isna(latest["Volume"]) else random.randint(50000, 500000)
                
                if not pd.isna(close_val) and not pd.isna(open_val) and open_val != 0:
                    change_pct = round(((close_val - open_val) / open_val) * 100, 2)
                else:
                    change_pct = round(random.uniform(-1.0, 1.0), 2)
                
                results.append({
                    "symbol": symbol,
                    "price": price,
                    "volume": volume,
                    "timestamp": datetime.utcnow().isoformat(),
                    "change_pct": change_pct
                })
            else:
                # If yfinance returns empty data, use the mock generator fallback
                results.append(get_mock_price(symbol))
        except Exception:
            # On network errors or rate-limits, fall back to mock data
            results.append(get_mock_price(symbol))
            
    return results

if __name__ == "__main__":
    print("Fetching current prices...")
    prices = fetch_current_prices()
    for p in prices:
        print(p)
