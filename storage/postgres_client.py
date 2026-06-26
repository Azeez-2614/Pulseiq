from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
import hashlib
from datetime import datetime
import sys
import os

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

Base = declarative_base()

# Global variables for session and engine initialization
_engine = None
_SessionFactory = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(config.POSTGRES_URL)
    return _engine

def get_session():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory()

class SentimentScore(Base):
    __tablename__ = "sentiment_scores"
    id = Column(String, primary_key=True)
    symbol = Column(String, index=True)
    source = Column(String)           # "news", "reddit", or source name
    headline = Column(String)
    compound = Column(Float)
    label = Column(String)
    published_at = Column(DateTime)
    scored_at = Column(DateTime)
    raw_scores = Column(JSON)         # Full sentiment scores dictionary

def init_db():
    """Initializes the database and creates all tables."""
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        print("PostgreSQL tables initialized successfully.")
        return True
    except Exception as e:
        print(f"Error initializing PostgreSQL database: {e}")
        return False

def save_scores(scored_articles: list[dict]):
    """
    Saves or updates sentiment scores in the PostgreSQL database.
    If an article mentions multiple tickers, a record is stored for each ticker.
    """
    try:
        session = get_session()
    except Exception as e:
        print(f"PostgreSQL connection failed during save_scores: {e}")
        return

    try:
        for article in scored_articles:
            # Get list of mentioned symbols, defaulting to ['GENERAL']
            symbols = article.get("mentioned_tickers", ["GENERAL"])
            if not symbols:
                symbols = ["GENERAL"]
                
            title = article.get("title", "")
            title_hash = hashlib.md5(title.encode("utf-8")).hexdigest()
            
            # published_at and scored_at handling (string to datetime)
            pub_at = article.get("published_at")
            if isinstance(pub_at, str):
                pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
                
            sc_at = article.get("scored_at")
            if isinstance(sc_at, str):
                sc_at = datetime.fromisoformat(sc_at.replace("Z", "+00:00"))

            for symbol in symbols:
                # Deterministic primary key
                row_id = f"{symbol}_{title_hash}"
                row = SentimentScore(
                    id=row_id,
                    symbol=symbol,
                    source=article.get("source", "unknown"),
                    headline=title[:500],  # Truncate if extremely long
                    compound=article["sentiment"]["compound"],
                    label=article["sentiment"]["label"],
                    published_at=pub_at,
                    scored_at=sc_at,
                    raw_scores=article["sentiment"]
                )
                session.merge(row)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error saving scores to PostgreSQL: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    from datetime import datetime
    print("Testing PostgreSQL connection and table initialization...")
    if init_db():
        # Insert a sample score
        sample_article = {
            "title": "Test Apple stock performance today",
            "source": "Bloomberg",
            "published_at": datetime.utcnow().isoformat(),
            "scored_at": datetime.utcnow().isoformat(),
            "mentioned_tickers": ["AAPL"],
            "sentiment": {"compound": 0.85, "positive": 0.9, "negative": 0.0, "neutral": 0.1, "label": "positive"}
        }
        save_scores([sample_article])
        print("Sample scores saved successfully.")
