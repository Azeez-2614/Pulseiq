import pandas as pd
from datetime import datetime, timedelta
from processing.correlator import compute_correlation

def test_compute_correlation_success():
    # Setup some correlated mock data for AAPL
    now = datetime.utcnow()
    timestamps = [now - timedelta(hours=i) for i in range(5)]
    
    sentiments = []
    prices = []
    
    # Perfectly positively correlated: sentiment compound increases, price change_pct increases
    for i, ts in enumerate(timestamps):
        sentiments.append({
            "published_at": ts.isoformat(),
            "mentioned_tickers": ["AAPL"],
            "sentiment": {"compound": float(5 - i)}
        })
        prices.append({
            "symbol": "AAPL",
            "timestamp": ts.isoformat(),
            "change_pct": float(5 - i)
        })
        
    sent_df = pd.DataFrame(sentiments)
    price_df = pd.DataFrame(prices)
    
    results = compute_correlation(sent_df, price_df)
    assert "AAPL" in results
    assert results["AAPL"]["status"] == "success"
    assert results["AAPL"]["correlation"] == 1.0
    assert results["AAPL"]["data_points"] == 5

def test_compute_correlation_empty_inputs():
    results = compute_correlation(pd.DataFrame(), pd.DataFrame())
    assert results == {}

def test_compute_correlation_zero_variance():
    now = datetime.utcnow()
    timestamps = [now - timedelta(hours=i) for i in range(5)]
    
    sentiments = []
    prices = []
    
    for i, ts in enumerate(timestamps):
        sentiments.append({
            "published_at": ts.isoformat(),
            "mentioned_tickers": ["AAPL"],
            "sentiment": {"compound": 0.5}  # constant sentiment
        })
        prices.append({
            "symbol": "AAPL",
            "timestamp": ts.isoformat(),
            "change_pct": float(i)
        })
        
    sent_df = pd.DataFrame(sentiments)
    price_df = pd.DataFrame(prices)
    
    results = compute_correlation(sent_df, price_df)
    assert "AAPL" in results
    assert results["AAPL"]["status"] == "zero_variance"
    assert results["AAPL"]["correlation"] == 0.0

def test_compute_correlation_too_few_data_points():
    now = datetime.utcnow()
    timestamps = [now - timedelta(hours=i) for i in range(2)]  # Only 2 points
    
    sentiments = []
    prices = []
    
    for i, ts in enumerate(timestamps):
        sentiments.append({
            "published_at": ts.isoformat(),
            "mentioned_tickers": ["AAPL"],
            "sentiment": {"compound": float(i)}
        })
        prices.append({
            "symbol": "AAPL",
            "timestamp": ts.isoformat(),
            "change_pct": float(i)
        })
        
    sent_df = pd.DataFrame(sentiments)
    price_df = pd.DataFrame(prices)
    
    results = compute_correlation(sent_df, price_df)
    assert "AAPL" not in results  # Requires at least 3 aligned points
