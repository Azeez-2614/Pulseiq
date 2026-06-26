import os
import random
from datetime import datetime, timedelta
import sys

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

try:
    import praw
except ImportError:
    praw = None

SUBREDDITS = ["wallstreetbets", "investing", "stocks"]
STOCK_KEYWORDS = ["AAPL", "TSLA", "GOOGL", "earnings", "bull", "bear", "crash"]

MOCK_REDDIT_POSTS = {
    "wallstreetbets": [
        ("AAPL is going to the moon! Earnings next week are going to be absolutely insane! 🚀🚀🚀", 1240, 342, "AAPL"),
        ("TSLA bear case: competition in China is destroying margins, get ready for a crash. I'm buying puts.", 850, 480, "TSLA"),
        ("My GOOGL options are printing today! Easiest money of my life, total breakout!", 980, 215, "GOOGL"),
        ("Is MSFT a buy at these levels or are we in a massive tech bubble?", 450, 190, "MSFT"),
        ("AMZN earnings play: solid guidance, AWS cloud growth is accelerating. Bullish!", 670, 112, "AMZN")
    ],
    "investing": [
        ("Long-term outlook on Apple (AAPL) post WWDC announcements. What are your thoughts?", 230, 89, "AAPL"),
        ("Why the Federal Reserve's current inflation stance means a bearish market for 2026.", 512, 241, "Federal Reserve"),
        ("Google (GOOGL) AI integration and its long term impact on ad-revenues.", 340, 120, "GOOGL"),
        ("Microsoft (MSFT) cloud revenue growth slowing down? A detailed analytical breakdown.", 180, 54, "MSFT")
    ],
    "stocks": [
        ("Tesla (TSLA) Q2 delivery report discussion thread. Strong bullish momentum?", 320, 150, "TSLA"),
        ("Tech stocks sell-off: AAPL, MSFT, and AMZN all down 2% today in pre-market.", 290, 75, "AAPL"),
        ("Why Amazon (AMZN) is the strongest e-commerce and cloud buy in the market right now.", 410, 95, "AMZN"),
        ("Inflation concerns return: How interest rates will impact growth stocks.", 150, 45, "inflation")
    ]
}

def generate_mock_reddit_posts() -> list[dict]:
    """Generates realistic mock Reddit posts if PRAW credentials are not set."""
    posts = []
    now = datetime.utcnow()
    
    for sub_name in SUBREDDITS:
        mock_posts = MOCK_REDDIT_POSTS.get(sub_name, [])
        # Pick 2-3 random posts per subreddit
        selected = random.sample(mock_posts, min(3, len(mock_posts)))
        for i, (title, score, comments, kw) in enumerate(selected):
            created_time = now - timedelta(hours=random.randint(1, 12), minutes=random.randint(0, 59))
            posts.append({
                "title": title,
                "score": score + random.randint(-50, 50),
                "num_comments": comments + random.randint(-20, 20),
                "subreddit": sub_name,
                "url": f"https://reddit.com/r/{sub_name}/comments/mockid{i}",
                "created_at": created_time.isoformat()
            })
    return posts

def fetch_reddit_posts() -> list[dict]:
    # Check if credentials are empty
    has_creds = config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET
    
    if not has_creds or praw is None:
        # print("Reddit API credentials missing or PRAW not installed. Using mock data.")
        return generate_mock_reddit_posts()

    posts = []
    try:
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT
        )
        
        for sub_name in SUBREDDITS:
            subreddit = reddit.subreddit(sub_name)
            # Fetch hot posts
            for post in subreddit.hot(limit=25):
                # Filter posts by stock keywords or watchlist symbols
                matches_kw = any(kw.lower() in post.title.lower() for kw in STOCK_KEYWORDS)
                matches_symbol = any(sym.lower() in post.title.lower() for sym in config.WATCHLIST)
                
                if matches_kw or matches_symbol:
                    posts.append({
                        "title": post.title,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "subreddit": sub_name,
                        "url": post.url,
                        # Convert UTC timestamp to ISO format string
                        "created_at": datetime.utcfromtimestamp(post.created_utc).isoformat()
                    })
    except Exception as e:
        # print(f"Error fetching from Reddit API: {e}. Falling back to mock data.")
        return generate_mock_reddit_posts()
        
    return posts

if __name__ == "__main__":
    print("Fetching Reddit posts...")
    posts = fetch_reddit_posts()
    for p in posts[:5]:
        print(f"[r/{p['subreddit']}] (Score: {p['score']}) {p['title']}")
