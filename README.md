# PulseIQ — Real-Time Market Sentiment Intelligence

![PulseIQ Dashboard](/Users/azeezk/.gemini/antigravity/brain/8de9d080-518e-40a6-96d0-09814fca0529/pulseiq_dashboard_1782476661808.png)

A production-grade Python platform that ingests live financial news, Reddit posts, and stock prices, runs NLP sentiment analysis, and exposes results via a REST API and real-time WebSocket stream.

## Tech Stack
* **Backend & API**: Python, FastAPI, WebSockets
* **Data Processing**: Pandas, SciPy, VADER / FinBERT Sentiment Engines
* **Databases**: PostgreSQL (Relational scores), Redis (Real-time cache & Pub/Sub), MongoDB (Raw JSON backups)
* **Frontend**: Next.js 14 (App Router) · TypeScript · Tailwind CSS · Framer Motion · Recharts · shadcn/ui
* **Containerization**: Docker · Docker Compose

## Architecture
Ingestion (NewsAPI + Reddit + yfinance) → NLP Processing (VADER/FinBERT) → Storage (PostgreSQL + Redis + MongoDB) → FastAPI REST + WebSocket → Next.js 14 Dashboard

## Quick Start

### Backend Setup
```bash
cp .env.example .env
pip install -r requirements.txt
python scheduler.py &
uvicorn api.main:app --reload &
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/scores` | All current sentiment scores |
| GET | `/scores/{symbol}` | Score for one ticker |
| GET | `/articles` | Recent scored articles |
| GET | `/correlation` | Pearson correlations and p-values |
| POST | `/pipeline/trigger` | Trigger ingestion pipeline asynchronously |
| WS | `/ws/live` | Real-time score stream |

## Docker
Run the entire multi-container service stack (Databases, API, Scheduler, and Frontend) in one command:
```bash
docker-compose up --build
```
