# PulseIQ — Real-Time Market Sentiment Intelligence

A production-grade Python platform that ingests live financial news, Reddit posts, and stock prices, runs NLP sentiment analysis, and exposes results via a REST API and real-time WebSocket stream.

## Tech Stack
Python · FastAPI · PostgreSQL · Redis · MongoDB · VADER/FinBERT · APScheduler · Streamlit · Docker

## Architecture
Ingestion (NewsAPI + Reddit + yfinance) → NLP Processing (VADER/FinBERT) → Storage (PostgreSQL + Redis + MongoDB) → FastAPI REST + WebSocket → Streamlit Dashboard

## Quick Start
```bash
cp .env.example .env
pip install -r requirements.txt
python scheduler.py
uvicorn api.main:app --reload
streamlit run dashboard/app.py
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/scores` | All current sentiment scores |
| GET | `/scores/{symbol}` | Score for one ticker |
| GET | `/articles` | Recent scored articles |
| WS | `/ws/live` | Real-time score stream |

## Docker
```bash
docker-compose up --build
```
