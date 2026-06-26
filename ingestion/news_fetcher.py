import requests
import os
import random
from datetime import datetime, timedelta
import sys

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

BASE_URL = "https://newsapi.org/v2/everything"
QUERY_TERMS = ["stock market", "AAPL", "TSLA", "Federal Reserve", "inflation"]

MOCK_HEADLINES = {
    "stock market": [
        ("Wall Street rallies as tech stocks lead market recovery", "Major indexes closed higher today as technology stocks rebounded strongly on positive earnings forecasts.", "Bloomberg"),
        ("Global stocks face volatility amid rising geopolitical tensions", "Investors are shifting portfolios to defensive assets as international conflicts introduce market uncertainty.", "Reuters"),
        ("Investors brace for market volatility ahead of key economic data", "Trading volume remained thin today as investors look ahead to CPI inflation figures due later this week.", "CNBC"),
        ("Small-cap stocks show strength, outperforming major indexes", "A surprising surge in small-cap companies indicates expanding market breadth, analysts say.", "MarketWatch")
    ],
    "AAPL": [
        ("Apple unveils groundbreaking AI integration at WWDC, shares jump", "Apple introduced new on-device artificial intelligence features that could spark a major iPhone upgrade cycle.", "TechCrunch"),
        ("Supply chain delays could impact iPhone shipments next quarter", "Analysts warn of potential assembly bottlenecks in key production hubs, possibly reducing holiday inventories.", "Wall Street Journal"),
        ("Apple services revenue hits record high, beating expectations", "Strong performance in App Store subscriptions and Apple Pay cushions the company against slowing hardware sales.", "CNBC"),
        ("Apple faces antitrust lawsuit over App Store policies", "Regulatory pressures increase as the government alleges anti-competitive behavior in Apple's developer ecosystem.", "Reuters")
    ],
    "TSLA": [
        ("Tesla vehicle deliveries beat Wall Street estimates in Q2", "Tesla shares surged after reporting quarterly delivery numbers that surpassed consensus expectations.", "CNBC"),
        ("Tesla faces safety probe over next-generation Autopilot software", "Federal regulators have opened an investigation into driver-assist systems following recent crash reports.", "Bloomberg"),
        ("Elon Musk announces next-generation Gigafactory expansion plans", "Tesla is set to invest billions in expanding its production capacity across North America and Europe.", "Reuters"),
        ("Tesla lowers prices in China to combat rising EV competition", "The price cuts highlight intensifying competition from domestic EV manufacturers like BYD.", "Wall Street Journal")
    ],
    "Federal Reserve": [
        ("Federal Reserve hints at rate cuts as inflation begins to cool", "Minutes from the latest Fed meeting suggest policy makers see progress on inflation, paving the way for cuts.", "Bloomberg"),
        ("Fed chairman signals higher-for-longer interest rate stance", "In a press conference today, Powell warned that interest rates may need to remain elevated if inflation persists.", "Reuters"),
        ("Fed meeting looms: What economists expect for interest rates", "Markets expect the central bank to hold rates steady, but all eyes are on policy forward guidance.", "CNBC")
    ],
    "inflation": [
        ("Inflation cools to lowest level in two years, boosting market hopes", "Consumer price index showed a lower-than-expected increase, driving optimistic sentiment on Wall Street.", "Wall Street Journal"),
        ("Rising energy costs push core inflation higher than expected", "Higher oil and gas prices are complicating the central bank's efforts to bring inflation to its 2% target.", "CNBC"),
        ("Consumer spending remains resilient despite ongoing inflation pressures", "Retail sales data beat expectations, showing that consumers continue to spend in spite of higher prices.", "MarketWatch")
    ]
}

def generate_mock_headlines() -> list[dict]:
    """Generates realistic mock financial headlines when API key is missing."""
    articles = []
    # Generate headlines for yesterday and today
    now = datetime.utcnow()
    
    for term in QUERY_TERMS:
        headlines = MOCK_HEADLINES.get(term, [])
        # Pick 2 random headlines per query term to simulate live ingestion
        selected = random.sample(headlines, min(2, len(headlines)))
        for i, (title, desc, source) in enumerate(selected):
            # Stagger timestamps slightly
            pub_time = now - timedelta(hours=random.randint(1, 23), minutes=random.randint(0, 59))
            articles.append({
                "title": title,
                "description": desc,
                "source": source,
                "url": f"https://mocknews.com/{term.lower().replace(' ', '-')}-{i}",
                "published_at": pub_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "query_term": term,
                "fetched_at": now.isoformat()
            })
    return articles

def fetch_headlines() -> list[dict]:
    if not config.NEWS_API_KEY:
        # print("NEWS_API_KEY not found in config. Using mock data generator.")
        return generate_mock_headlines()
        
    articles = []
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    for term in QUERY_TERMS:
        try:
            resp = requests.get(BASE_URL, params={
                "q": term,
                "from": yesterday,
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": config.NEWS_API_KEY,
                "pageSize": 10
            })
            if resp.status_code != 200:
                # If rate-limited or bad status, fail gracefully and fall back to mock
                continue
            for article in resp.json().get("articles", []):
                articles.append({
                    "title": article["title"],
                    "description": article.get("description", "") or "",
                    "source": article["source"]["name"] if isinstance(article.get("source"), dict) else "Unknown",
                    "url": article["url"],
                    "published_at": article["publishedAt"],
                    "query_term": term,
                    "fetched_at": datetime.utcnow().isoformat()
                })
        except Exception:
            # If network request fails, we skip that term (or we could return mocks)
            pass
            
    # If API requests failed or returned no articles, fallback to mock data
    if not articles:
        return generate_mock_headlines()
        
    return articles

if __name__ == "__main__":
    print("Fetching headlines...")
    articles = fetch_headlines()
    for a in articles[:5]:
        print(f"[{a['query_term']}] {a['title']} - {a['source']}")
