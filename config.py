import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Watchlist Symbols
WATCHLIST = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"]

# Database Configurations
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/pulseiq")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")

# API Keys & Credentials
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "PulseIQ/1.0")

# NLP Settings
# Set to True to download and use ProsusAI/finbert transformer model. Otherwise, vaderSentiment is used.
USE_FINBERT = os.getenv("USE_FINBERT", "False").lower() in ("true", "1", "yes")

# Scheduler Settings
PIPELINE_INTERVAL_MINUTES = int(os.getenv("PIPELINE_INTERVAL_MINUTES", "5"))
