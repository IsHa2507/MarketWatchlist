# MarketPulse

> **Watch less. Understand more.**

MarketPulse is a smart stock watchlist that tells you *what actually changed* since your last visit — ranked by importance, with plain-English explanations. Not another dashboard full of numbers you have to interpret yourself.

---

## The Problem

Traditional watchlists expose raw data — prices, percentages, charts — but leave all the interpretation to you. After a few days away, you're left asking:

- What actually changed?
- Is it important?
- Why did it change?
- What should I look at first?

## The Solution

MarketPulse detects meaningful changes since your last visit using a **checkpointing system**, ranks them using an explainable **Attention Score**, and tells you *why* each change matters — in plain English.

---

## Features

| Feature | Description |
|---|---|
| **Since You Last Checked** | Compares current state with your previous visit's checkpoint |
| **Attention Score** | Weighted 0–100 score (price 35% + volume 20% + sentiment 20% + volatility 15% + technical 10%) |
| **Classification** | CRITICAL / IMPORTANT / WORTH WATCHING / NORMAL |
| **AI Explanations** | LLM-generated explanations (falls back to templates without API key) |
| **Score Breakdown** | Every score is explainable with per-component bars |
| **Price & Volume Charts** | Recharts with "Last Check" reference marker |
| **News & Events** | Per-stock market events with impact scores and sentiment |
| **Demo Mode** | Fully working without any paid APIs |
| **Responsive** | Works on desktop, tablet, and mobile |

---

## Architecture

```mermaid
graph TD
    Browser["Browser (React + Vite)"]
    API["FastAPI Backend"]
    DB[(PostgreSQL)]
    MDS["MarketDataService\n(Demo / Live)"]
    CDS["ChangeDetectionService"]
    ASS["AttentionScoringService"]
    ES["ExplanationService\n(LLM / Template)"]
    CP["UserCheckpoint Table"]

    Browser -->|REST + JWT| API
    API --> DB
    API --> MDS
    API --> CDS
    CDS --> CP
    CDS --> MDS
    API --> ASS
    API --> ES
```

---

## Tech Stack

**Frontend**
- React 18 + TypeScript + Vite
- Tailwind CSS (dark theme)
- React Router v6
- Recharts
- Axios
- Lucide React

**Backend**
- Python 3.11 + FastAPI
- SQLAlchemy 2.0 + PostgreSQL
- Pydantic v2
- JWT (python-jose) + bcrypt
- APScheduler (optional)

---

## Database Schema

```
users              watchlists         watchlist_stocks
──────             ──────────         ────────────────
id                 id                 id
email              user_id →          watchlist_id →
password_hash      name               ticker
full_name          created_at         added_at
created_at         updated_at
last_seen_at

stock_snapshots    market_events      user_checkpoints
───────────────    ─────────────      ────────────────
id                 id                 id
ticker             ticker             user_id →
price              event_type         ticker
price_change_pct   title              price
volume             description        volume
average_volume     sentiment          volatility
volatility         impact_score       sentiment_score
sentiment_score    source             checked_at
timestamp          timestamp
```

---

## Attention Score Formula

```
Attention Score =
    35% × Price Movement Score
  + 20% × Volume Anomaly Score
  + 20% × News/Sentiment Score
  + 15% × Volatility Change Score
  + 10% × Technical Signal Score

Classification:
  81–100  →  CRITICAL
  61–80   →  IMPORTANT
  31–60   →  WORTH WATCHING
   0–30   →  NORMAL
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register |
| POST | `/auth/login` | Login (returns JWT) |
| GET | `/auth/me` | Current user |
| GET | `/watchlists` | List watchlists |
| POST | `/watchlists` | Create watchlist |
| PUT | `/watchlists/{id}` | Rename |
| DELETE | `/watchlists/{id}` | Delete |
| POST | `/watchlists/{id}/stocks` | Add stock |
| DELETE | `/watchlists/{id}/stocks/{ticker}` | Remove stock |
| GET | `/stocks/search?q=` | Search stocks |
| GET | `/stocks/{ticker}` | Quote |
| GET | `/stocks/{ticker}/history` | Price history |
| GET | `/stocks/{ticker}/events` | News/events |
| GET | `/dashboard` | Full dashboard (runs checkpoint logic) |
| GET | `/dashboard/changes` | Changed stocks only |
| GET | `/dashboard/attention` | Needs-attention stocks |

---

## Local Setup

### Option 1 — Docker Compose (recommended)

```bash
cd marketpulse
cp .env.example .env       # edit if needed
docker compose up --build
```

Then open:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

Seed demo data:
```bash
docker compose exec backend python seed/seed.py
```

### Option 2 — Manual

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env    # set DATABASE_URL
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

**Seed:**
```bash
cd ..
python seed/seed.py
```

---

## Environment Variables

```env
DATABASE_URL=postgresql://marketpulse:marketpulse@localhost:5432/marketpulse
JWT_SECRET=your-secret
DEMO_MODE=true              # use seeded data (no paid API needed)

# Optional — leave empty to use demo mode
MARKET_API_KEY=
NEWS_API_KEY=
LLM_API_KEY=                # OpenAI key for AI explanations
LLM_PROVIDER=openai
```

---

## Demo Instructions

1. `docker compose up --build`
2. Seed data: `docker compose exec backend python seed/seed.py`
3. Open http://localhost:3000
4. Login: `demo@marketpulse.app` / `demo123`
5. Dashboard shows changes since 3 days ago:
   - 🔴 TCS: -3.8%, vol 2.1x, negative sentiment → **Attention Score 79**
   - 🔴 NVDA: +6.2%, vol 2.8x, positive sentiment → **Attention Score ~80**
   - 🟡 RELIANCE: +2.4%, vol 1.8x → **Worth Watching**
   - 🟢 INFY, HDFC, TSLA → **Nothing Significant**
6. Click TCS → see full breakdown, chart, events, explanation

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

All 26 tests cover: auth, watchlist CRUD, attention scoring scenarios, checkpoint ordering.

---

## Future Improvements

- Real-time price websocket feed
- Price alerts (email/push)
- Portfolio P&L tracking
- Multi-language support
- Mobile app (React Native)
- Advanced technical indicators (RSI, MACD)
- Collaborative watchlists
