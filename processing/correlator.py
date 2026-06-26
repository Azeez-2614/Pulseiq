import pandas as pd
import numpy as np
from scipy.stats import pearsonr
import sys
import os

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def compute_correlation(sentiment_df: pd.DataFrame, price_df: pd.DataFrame) -> dict:
    """
    Correlate average hourly sentiment with % price change for each ticker.
    Returns Pearson correlation coefficient, p-value, and status per symbol.
    """
    results = {}

    if sentiment_df.empty or price_df.empty:
        return results

    # Ensure sentiment_df published_at is datetime
    sentiment_df = sentiment_df.copy()
    sentiment_df["published_at"] = pd.to_datetime(
        sentiment_df["published_at"], utc=True
    )

    # Ensure price_df timestamp is datetime
    price_df = price_df.copy()
    price_df["timestamp"] = pd.to_datetime(price_df["timestamp"], utc=True)

    for symbol in config.WATCHLIST:
        # Filter articles mentioning this ticker
        sym_articles = sentiment_df[
            sentiment_df["mentioned_tickers"].apply(
                lambda t: symbol in t if isinstance(t, list) else False
            )
        ].copy()

        if len(sym_articles) < 3:  # Not enough articles
            continue

        # Extract compound score from sentiment dict
        def get_compound(x):
            if isinstance(x, dict):
                return x.get("compound", 0.0)
            return 0.0

        sym_articles["compound_sentiment"] = sym_articles["sentiment"].apply(
            get_compound
        )

        # Resample sentiment to hourly buckets
        sym_articles = sym_articles.set_index("published_at")
        hourly_sentiment = (
            sym_articles["compound_sentiment"].resample("1h").mean().dropna()
        )

        # Match with hourly price changes
        sym_prices = price_df[price_df["symbol"] == symbol].copy()
        if sym_prices.empty:
            continue

        sym_prices = (
            sym_prices.set_index("timestamp")["change_pct"]
            .resample("1h")
            .last()
            .dropna()
        )

        if hourly_sentiment.empty or sym_prices.empty:
            continue

        # Align both series on the same hourly timestamps
        aligned = pd.concat([hourly_sentiment, sym_prices], axis=1).dropna()
        aligned.columns = ["sentiment", "price_change"]

        # We need at least 3 data points to compute a correlation coefficient
        if len(aligned) < 3:
            continue

        # Defensive check: if variance of either column is zero, pearsonr returns NaN or raises an error
        if aligned["sentiment"].std() == 0 or aligned["price_change"].std() == 0:
            results[symbol] = {
                "correlation": 0.0,
                "p_value": 1.0,
                "data_points": len(aligned),
                "significant": False,
                "status": "zero_variance",
            }
            continue

        try:
            corr, p_value = pearsonr(aligned["sentiment"], aligned["price_change"])

            # Handle NaN values returned by pearsonr
            if np.isnan(corr) or np.isnan(p_value):
                corr = 0.0
                p_value = 1.0

            results[symbol] = {
                "correlation": round(float(corr), 4),
                "p_value": round(float(p_value), 4),
                "data_points": len(aligned),
                "significant": p_value < 0.05,
                "status": "success",
            }
        except Exception as e:
            results[symbol] = {
                "correlation": 0.0,
                "p_value": 1.0,
                "data_points": len(aligned),
                "significant": False,
                "status": f"error: {str(e)}",
            }

    return results


if __name__ == "__main__":
    # Quick test setup
    import random
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    # Generate 5 hours of aligned sentiment and price data for AAPL
    timestamps = [now - timedelta(hours=i) for i in range(5)]

    mock_sentiments = []
    mock_prices = []

    for ts in timestamps:
        # Sentiment articles
        mock_sentiments.append(
            {
                "title": f"Test Apple Article at {ts}",
                "published_at": ts.isoformat(),
                "mentioned_tickers": ["AAPL"],
                "sentiment": {"compound": random.uniform(-1, 1)},
            }
        )
        # Price records
        mock_prices.append(
            {
                "symbol": "AAPL",
                "timestamp": ts.isoformat(),
                "change_pct": random.uniform(-2, 2),
            }
        )

    sent_df = pd.DataFrame(mock_sentiments)
    price_df = pd.DataFrame(mock_prices)

    corr_results = compute_correlation(sent_df, price_df)
    print("Correlation results:")
    print(corr_results)
