import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

TICKER_MAPPINGS = {
    "AAPL": ["AAPL", "APPLE"],
    "TSLA": ["TSLA", "TESLA"],
    "GOOGL": ["GOOGL", "GOOGLE", "ALPHABET"],
    "MSFT": ["MSFT", "MICROSOFT"],
    "AMZN": ["AMZN", "AMAZON"]
}

def find_mentioned_tickers(text: str) -> list[str]:
    """Scans text for stock tickers or company names and returns matching ticker symbols."""
    text_upper = str(text).upper()
    mentioned = []
    for ticker, aliases in TICKER_MAPPINGS.items():
        for alias in aliases:
            # Simple check, but avoid matching letters inside other words.
            # E.g., we want to match "TSLA", but not "ATSLAD"
            # For simplicity, we can do substring check or word boundary checks.
            # Since financial headlines are short, substring check works well.
            if alias in text_upper:
                mentioned.append(ticker)
                break  # Go to next ticker if this one matched
    return mentioned if mentioned else ["GENERAL"]

def normalize_articles(raw_articles: list[dict]) -> pd.DataFrame:
    """
    Standardizes a list of article/post dictionaries into a uniform Pandas DataFrame.
    Fills missing values, extracts mentioned tickers, and standardizes timestamps.
    """
    if not raw_articles:
        return pd.DataFrame(columns=["title", "description", "source", "published_at",
                                     "sentiment", "mentioned_tickers", "url", "scored_at"])
                                     
    df = pd.DataFrame(raw_articles)
    
    # 1. Standardize timestamp (NewsAPI uses 'published_at', Reddit uses 'created_at')
    if "published_at" not in df.columns:
        df["published_at"] = None
        
    if "created_at" in df.columns:
        df["published_at"] = df["published_at"].fillna(df["created_at"])
        
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    df = df.dropna(subset=["published_at"])
    
    # 2. Drop duplicates by title to prevent scoring the exact same content twice
    df = df.drop_duplicates(subset=["title"])
    
    # 3. Fill missing fields
    if "description" not in df.columns:
        df["description"] = ""
    df["description"] = df["description"].fillna("")
    
    if "source" not in df.columns:
        df["source"] = "unknown"
    df["source"] = df["source"].fillna("unknown")
    
    if "url" not in df.columns:
        df["url"] = ""
    df["url"] = df["url"].fillna("")
    
    if "scored_at" not in df.columns:
        df["scored_at"] = datetime.utcnow().isoformat()
    df["scored_at"] = df["scored_at"].fillna(datetime.utcnow().isoformat())
    
    # 4. Extract mentioned tickers
    def extract_tickers(row):
        combined_text = f"{row.get('title', '')} {row.get('description', '')}"
        # If the article has a query_term that is a watchlist ticker, make sure to include it
        tickers = find_mentioned_tickers(combined_text)
        query_term = row.get("query_term", "")
        if query_term in config.WATCHLIST and query_term not in tickers:
            if "GENERAL" in tickers:
                tickers.remove("GENERAL")
            tickers.append(query_term)
        return tickers

    df["mentioned_tickers"] = df.apply(extract_tickers, axis=1)
    
    # Keep only the standardized schema columns
    schema_cols = ["title", "description", "source", "published_at",
                   "sentiment", "mentioned_tickers", "url", "scored_at"]
                   
    # Ensure all schema columns exist in df
    for col in schema_cols:
        if col not in df.columns:
            df[col] = None
            
    return df[schema_cols]

if __name__ == "__main__":
    # Test normalization
    test_data = [
        {
            "title": "Microsoft (MSFT) is leading the AI race",
            "description": "Tech giant Microsoft announces new Azure features.",
            "source": "TechCrunch",
            "published_at": "2026-06-26T08:00:00Z",
            "sentiment": {"compound": 0.5, "label": "positive"},
            "url": "https://techcrunch.com/msft"
        },
        {
            "title": "TSLA stock crashes after safety probe",
            "source": "wallstreetbets",
            "created_at": "2026-06-26T09:30:00Z",
            "sentiment": {"compound": -0.8, "label": "negative"},
            "url": "https://reddit.com/r/wsb"
        }
    ]
    df = normalize_articles(test_data)
    print("Standardized DataFrame:")
    print(df[["title", "published_at", "source", "mentioned_tickers"]])
