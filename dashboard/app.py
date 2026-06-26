import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
import sys
import os

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Page config
st.set_page_config(
    page_title="PulseIQ — Market Sentiment & Stock Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Custom CSS for Premium Design & Glassmorphism
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

/* Target main Streamlit container */
.stApp {
    background-color: #0b0f19 !important;
    color: #f3f4f6 !important;
    font-family: 'Outfit', sans-serif !important;
}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {
    background-color: #0f172a !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
}

/* Gradient Header */
.header-container {
    padding: 1.5rem 0;
    text-align: center;
    background: radial-gradient(circle at 50% 50%, rgba(56, 189, 248, 0.1) 0%, rgba(15, 23, 42, 0) 80%);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    margin-bottom: 2rem;
}

.gradient-title {
    font-size: 3.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
    letter-spacing: -0.04em;
}

.subtitle {
    font-size: 1.1rem;
    color: #9ca3af;
    font-weight: 400;
}

/* Custom Card Container */
.glass-card {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.25rem;
    box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.25);
    margin-bottom: 1.25rem;
    transition: all 0.3s ease;
}

.glass-card:hover {
    transform: translateY(-2px);
    border-color: rgba(56, 189, 248, 0.3);
    box-shadow: 0 15px 35px 0 rgba(56, 189, 248, 0.05);
}

.card-ticker {
    font-size: 1.5rem;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.card-price {
    font-size: 1.8rem;
    font-weight: 800;
    margin: 0.4rem 0;
    color: #f9fafb;
}

.change-pill {
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    display: inline-block;
}

.pill-up {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.25);
}

.pill-down {
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.25);
}

.pill-flat {
    background: rgba(156, 163, 175, 0.15);
    color: #9ca3af;
    border: 1px solid rgba(156, 163, 175, 0.25);
}

/* Sentiment Bar CSS */
.sentiment-bar-container {
    width: 100%;
    background-color: rgba(255, 255, 255, 0.07);
    border-radius: 9999px;
    height: 8px;
    margin-top: 10px;
    overflow: hidden;
}

.sentiment-bar-fill {
    height: 100%;
    border-radius: 9999px;
}

/* News Article Card style */
.news-card {
    background: rgba(30, 41, 59, 0.35);
    border-left: 4px solid #818cf8;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.8rem;
    transition: all 0.2s ease;
}

.news-card:hover {
    background: rgba(30, 41, 59, 0.5);
}

.news-meta {
    font-size: 0.75rem;
    color: #9ca3af;
    margin-bottom: 0.4rem;
    display: flex;
    gap: 1rem;
}

.news-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #f3f4f6;
    line-height: 1.4;
    margin-bottom: 0.4rem;
}

.score-badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
}

.badge-pos {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
}

.badge-neg {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
}

.badge-neu {
    background: rgba(107, 114, 128, 0.25);
    color: #d1d5db;
}

/* Custom correlation metric */
.corr-val {
    font-size: 2rem;
    font-weight: 700;
    font-family: monospace;
}

.sig-active {
    color: #34d399;
    font-weight: bold;
}

.sig-inactive {
    color: #9ca3af;
}
</style>
""", unsafe_allow_html=True)

# Sidebar configurations
st.sidebar.markdown("<h3 style='color:#38bdf8;'>PulseIQ Controller</h3>", unsafe_allow_html=True)
st.sidebar.write("Configure and monitor backend services.")

# Server Health Status Check
try:
    health_resp = requests.get(f"{API_BASE}/health", timeout=2)
    server_online = health_resp.status_code == 200
except Exception:
    server_online = False

status_color = "#34d399" if server_online else "#f87171"
status_text = "Connected" if server_online else "Offline"
st.sidebar.markdown(f"**API Service:** <span style='color:{status_color}; font-weight:bold;'>{status_text}</span>", unsafe_allow_html=True)

# Watchlist info
st.sidebar.markdown("---")
st.sidebar.markdown("**Tracked Watchlist:**")
for s in config.WATCHLIST:
    st.sidebar.code(s)

# Pipeline Configs
st.sidebar.markdown("---")
st.sidebar.markdown("**NLP Sentiment Engine:**")
engine_name = "FinBERT (ProsusAI)" if config.USE_FINBERT else "VADER Sentiment"
st.sidebar.info(engine_name)

# Auto Refresh Toggle
auto_refresh = st.sidebar.toggle("Auto-Refresh Dashboard (10s)", value=True)

# Main Banner Header
st.markdown("""
<div class="header-container">
    <div class="gradient-title">PulseIQ</div>
    <div class="subtitle">Real-Time Market Sentiment & Stock Intelligence Pipeline</div>
</div>
""", unsafe_allow_html=True)

if not server_online:
    st.warning("⚠️ **FastAPI backend is offline.** To see real-time updates, please start your API server using:")
    st.code("uvicorn api.main:app --reload --port 8000")
    st.info("The dashboard is currently in **Mock Mode** using generated mock data for preview purposes.")
    
    # Generate mock dashboard data
    from ingestion.stock_fetcher import fetch_current_prices
    from ingestion.news_fetcher import generate_mock_headlines
    from processing.sentiment import score_batch
    from processing.normalizer import find_mentioned_tickers
    
    # 1. Mock scores
    scores_data = {}
    for s in config.WATCHLIST:
        prices = fetch_current_prices()
        p_info = next((p for p in prices if p["symbol"] == s), {"price": 100.0, "change_pct": 0.0, "volume": 0})
        scores_data[s] = {
            "symbol": s,
            "score": round(1.2 * ((hash(s) % 5) - 2) / 2, 2), # deterministic mock sentiment score
            "price": p_info.get("price"),
            "change_pct": p_info.get("change_pct"),
            "volume": p_info.get("volume")
        }
        
    # 2. Mock articles
    articles_data = []
    raw_mocks = generate_mock_headlines()
    scored_mocks = score_batch(raw_mocks)
    for a in scored_mocks[:6]:
        mentioned = find_mentioned_tickers(a["title"])
        articles_data.append({
            "title": a["title"],
            "source": a["source"],
            "published_at": a["published_at"],
            "symbol": mentioned[0] if mentioned else "GENERAL",
            "sentiment": a["sentiment"]
        })
        
    # 3. Mock correlations
    correlation_data = {
        "correlations": {
            "AAPL": {"correlation": 0.6854, "p_value": 0.012, "data_points": 24, "significant": True, "status": "success"},
            "TSLA": {"correlation": -0.4120, "p_value": 0.082, "data_points": 24, "significant": False, "status": "success"},
            "GOOGL": {"correlation": 0.1245, "p_value": 0.651, "data_points": 24, "significant": False, "status": "success"},
            "MSFT": {"correlation": 0.7241, "p_value": 0.003, "data_points": 24, "significant": True, "status": "success"},
            "AMZN": {"correlation": 0.3892, "p_value": 0.121, "data_points": 24, "significant": False, "status": "success"}
        }
    }
else:
    # Fetch data from FastAPI backend
    try:
        scores_data = requests.get(f"{API_BASE}/scores").json()
        articles_data = requests.get(f"{API_BASE}/articles?limit=6").json()
        correlation_data = requests.get(f"{API_BASE}/correlation").json()
        
        # If correlations not ready yet in API
        if "correlations" not in correlation_data:
            correlation_data = {"correlations": {}}
    except Exception as e:
        st.error(f"Failed to query API: {e}")
        st.stop()

# --- ROW 1: Watchlist Stock Cards ---
st.subheader("📊 Stock Watchlist & Sentiment Tracker")
cols = st.columns(len(config.WATCHLIST))

for i, symbol in enumerate(config.WATCHLIST):
    data = scores_data.get(symbol, {})
    price = data.get("price", 0.0)
    change = data.get("change_pct", 0.0)
    sent_score = data.get("score", 0.0)
    
    # Determine styles based on values
    change_class = "pill-up" if change > 0 else "pill-down" if change < 0 else "pill-flat"
    change_prefix = "+" if change > 0 else ""
    
    # Map sentiment score to progress bar color
    # -1 to +1 normalized to percentage 0% to 100%
    sent_pct = int(((sent_score + 1) / 2) * 100)
    
    if sent_score >= 0.05:
        sent_color = "#10b981" # Green
        sent_label = "Positive"
        sent_badge = "badge-pos"
    elif sent_score <= -0.05:
        sent_color = "#ef4444" # Red
        sent_label = "Negative"
        sent_badge = "badge-neg"
    else:
        sent_color = "#9ca3af" # Gray
        sent_label = "Neutral"
        sent_badge = "badge-neu"
        
    with cols[i]:
        st.markdown(f"""
        <div class="glass-card">
            <div class="card-ticker">
                <span>{symbol}</span>
                <span class="change-pill {change_class}">{change_prefix}{change:.2f}%</span>
            </div>
            <div class="card-price">${price:,.2f}</div>
            <div style="font-size: 0.8rem; color:#9ca3af; display:flex; justify-content:space-between; margin-top:0.5rem;">
                <span>Sentiment Score: <b>{sent_score:+.2f}</b></span>
                <span class="score-badge {sent_badge}">{sent_label}</span>
            </div>
            <div class="sentiment-bar-container">
                <div class="sentiment-bar-fill" style="width: {sent_pct}%; background-color: {sent_color};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- ROW 2: Charts & Analytics ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("<h3 style='margin-bottom:1rem;'>🔥 Aggregated Market Sentiment</h3>", unsafe_allow_html=True)
    
    # Construct DataFrame for Plotly
    plotly_data = []
    for sym in config.WATCHLIST:
        plotly_data.append({
            "Symbol": sym,
            "Sentiment Score": scores_data.get(sym, {}).get("score", 0.0)
        })
    df_sent = pd.DataFrame(plotly_data)
    
    # Assign custom colors: green for positive, red for negative
    df_sent["Color"] = df_sent["Sentiment Score"].apply(lambda x: "#10b981" if x >= 0.05 else ("#ef4444" if x <= -0.05 else "#9ca3af"))
    
    fig = px.bar(
        df_sent,
        x="Symbol",
        y="Sentiment Score",
        color="Symbol",
        color_discrete_sequence=df_sent["Color"].tolist(),
        range_y=[-1.0, 1.0],
        text="Sentiment Score"
    )
    
    fig.update_traces(textposition='outside', texttemplate='%{y:+.2f}')
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f3f4f6", family="Outfit"),
        showlegend=False,
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.2)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown("<h3 style='margin-bottom:1rem;'>📈 Price-Sentiment Correlations</h3>", unsafe_allow_html=True)
    
    corrs = correlation_data.get("correlations", {})
    if not corrs:
        st.info("Waiting for historical sentiment and stock data to compile. Correlations will show up after a few scheduler pipeline runs.")
    else:
        corr_list = []
        for symbol, info in corrs.items():
            corr_list.append({
                "Symbol": symbol,
                "Pearson Coefficient": info.get("correlation", 0.0),
                "P-Value": info.get("p_value", 1.0),
                "Status": "Significant (p < 0.05) ✅" if info.get("significant") else "Not Significant ❌"
            })
        df_corr = pd.DataFrame(corr_list)
        
        # Draw Plotly correlation comparison chart
        df_corr["Color"] = df_corr["Pearson Coefficient"].apply(lambda x: "#38bdf8" if x >= 0 else "#f87171")
        fig_corr = px.bar(
            df_corr,
            y="Symbol",
            x="Pearson Coefficient",
            orientation='h',
            range_x=[-1.0, 1.0],
            color="Symbol",
            color_discrete_sequence=df_corr["Color"].tolist(),
            text="Pearson Coefficient"
        )
        
        fig_corr.update_traces(textposition='inside', texttemplate='%{x:+.2f}')
        fig_corr.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f3f4f6", family="Outfit"),
            showlegend=False,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.2)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_corr, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- ROW 3: Live Feed & Stats ---
col_feed, col_stats = st.columns([2, 1])

with col_feed:
    st.markdown("<h3 style='margin-bottom:1rem;'>📰 Scored Sentiment Feed</h3>", unsafe_allow_html=True)
    
    if not articles_data:
        st.write("No articles scored yet. Pipeline is running...")
    else:
        for art in articles_data:
            sent = art.get("sentiment", {})
            compound = sent.get("compound", 0.0)
            label = sent.get("label", "neutral").lower()
            
            if label == "positive" or compound >= 0.05:
                badge_class = "badge-pos"
                sentiment_label = f"Positive ({compound:+.2f})"
            elif label == "negative" or compound <= -0.05:
                badge_class = "badge-neg"
                sentiment_label = f"Negative ({compound:+.2f})"
            else:
                badge_class = "badge-neu"
                sentiment_label = f"Neutral ({compound:+.2f})"
                
            pub_date = art.get("published_at", "")
            if pub_date:
                try:
                    # Clean up timestamp format
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    pub_date = pub_dt.strftime("%Y-%m-%d %H:%M UTC")
                except ValueError:
                    pass
            
            st.markdown(f"""
            <div class="news-card">
                <div class="news-meta">
                    <span><b>{art.get('source', 'Unknown')}</b></span>
                    <span>•</span>
                    <span>{pub_date}</span>
                    <span>•</span>
                    <span style="color:#38bdf8; font-weight:600;">{art.get('symbol', 'GENERAL')}</span>
                </div>
                <div class="news-title">{art.get('title')}</div>
                <div>
                    <span class="score-badge {badge_class}">{sentiment_label}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

with col_stats:
    st.markdown("<h3 style='margin-bottom:1rem;'>📊 Statistical Summary</h3>", unsafe_allow_html=True)
    
    # Render table of correlation details
    corrs = correlation_data.get("correlations", {})
    if not corrs:
        st.info("Run the scheduler to gather historical sentiment and price records.")
    else:
        summary_rows = []
        for symbol, info in corrs.items():
            summary_rows.append({
                "Ticker": symbol,
                "Pearson R": f"{info.get('correlation', 0.0):+.4f}",
                "P-Value": f"{info.get('p_value', 1.0):.4f}",
                "Sig.": "✅ Yes" if info.get("significant") else "❌ No"
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        
        # Detailed stats insights
        sig_count = sum(1 for info in corrs.values() if info.get("significant"))
        total_count = len(corrs)
        
        st.markdown(f"""
        <div class="glass-card" style="margin-top: 1rem; border-color: rgba(168, 85, 247, 0.2);">
            <div class="card-ticker" style="font-size:1.1rem; color:#c084fc;">Statistical Insights</div>
            <p style="font-size:0.85rem; color:#9ca3af; margin-top:0.5rem; line-height:1.4;">
                We found statistically significant correlations for <b>{sig_count} out of {total_count}</b> watchlist symbols.
                <br><br>
                A positive Pearson coefficient indicates stock price moves in the same direction as sentiment. A negative coefficient indicates inverse movement.
            </p>
        </div>
        """, unsafe_allow_html=True)

# Loop auto-refresh
if auto_refresh:
    time.sleep(10)
    st.rerun()
