from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Float, DateTime, JSON
import os
import hashlib
from datetime import datetime

Base = declarative_base()

DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql+asyncpg://postgres:postgres@localhost/pulseiq")

# Force asyncpg if default URL is passed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class SentimentScore(Base):
    __tablename__ = "sentiment_scores"
    id = Column(String, primary_key=True)
    symbol = Column(String, index=True)
    source = Column(String)
    headline = Column(String)
    compound = Column(Float)
    label = Column(String)
    published_at = Column(DateTime)
    scored_at = Column(DateTime)
    raw_scores = Column(JSON)

async def save_scores(scored_articles: list[dict]):
    """Asynchronously saves or updates scores in PostgreSQL using upsert (merge)."""
    async with AsyncSessionLocal() as session:
        try:
            for article in scored_articles:
                symbols = article.get("mentioned_tickers", ["GENERAL"])
                if not symbols:
                    symbols = ["GENERAL"]
                    
                title = article.get("title", "")
                title_hash = hashlib.md5(title.encode("utf-8")).hexdigest()
                
                # published_at and scored_at handling (string to datetime)
                pub_at = article.get("published_at")
                if isinstance(pub_at, str):
                    try:
                        pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
                    except ValueError:
                        pub_at = datetime.utcnow()
                elif pub_at is None:
                    pub_at = datetime.utcnow()
                    
                sc_at = article.get("scored_at")
                if isinstance(sc_at, str):
                    try:
                        sc_at = datetime.fromisoformat(sc_at.replace("Z", "+00:00"))
                    except ValueError:
                        sc_at = datetime.utcnow()
                elif sc_at is None:
                    sc_at = datetime.utcnow()

                for symbol in symbols:
                    row_id = f"{symbol}_{title_hash}"
                    row = SentimentScore(
                        id=row_id,
                        symbol=symbol,
                        source=article.get("source", "unknown"),
                        headline=title[:500],
                        compound=article["sentiment"]["compound"],
                        label=article["sentiment"]["label"],
                        published_at=pub_at,
                        scored_at=sc_at,
                        raw_scores=article["sentiment"]
                    )
                    await session.merge(row)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e

async def init_db():
    """Initializes tables for PostgreSQL."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
