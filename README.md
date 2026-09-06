# MarketPulse AI ⭐

> **Watch less. Understand more.**

[![GitHub](https://img.shields.io/badge/GitHub-IsHa2507%2FMarketWatchlist-blue?logo=github)](https://github.com/IsHa2507/MarketWatchlist)
[![Live Demo](https://img.shields.io/badge/Demo-Live-success?logo=vercel)](https://github.com/IsHa2507/MarketWatchlist)

MarketPulse AI is a smart market watchlist that tells you **what changed since you last checked — and whether it matters.**

Traditional watchlists show you the current price.  
MarketPulse AI compares the market's current state against the last time you visited, scores each change by significance, and explains it in plain language.

---

## The core idea

MarketPulse AI uses intelligent change detection and AI-powered explanations to surface what matters:

```
User visits dashboard
        ↓
MarketPulse AI reads the user's last checkpoint
        ↓
Fetches current market data
        ↓
Calculates what changed (price, volume, volatility, sentiment)
        ↓
Scores each stock 0–100 (AI Attention Score)
        ↓
Ranks and explains the changes
        ↓
Updates checkpoint for next visit
```

The checkpoint is **always read before it is updated**. The comparison is always against the previous state, never the current one.

---

## Features

- **AI-Powered Analysis** — intelligent change detection since your last visit
- **Attention Score** (0–100) — explainable weighted score across 5 signals
- **Classification** — CRITICAL / IMPORTANT / WORTH WATCHING / NORMAL
- **Why It Matters** — plain-language AI-generated explanations
- **Freshness indicators** — 🟢 Live · 🟡 Stale · ⚪ Market closed · 🔴 Error
- **Real market data** via yfinance (Indian NSE + US stocks)
- **Demo mode** — works fully offline with no API keys
- **Partial failure handling** — one broken stock never crashes the dashboard
- **Watchlist management** — create, rename, delete; add/remove stocks
- **Stock detail page** — price chart, volume chart, events, score breakdown

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│         React 18 · TypeScript · Vite · Tailwind         │
│  Dashboard · Stock Detail · Watchlists · Auth           │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP / REST
┌───────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                       │
│                                                         │
│  Routes: /auth  /watchlists  /stocks  /dashboard        │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              DashboardService                    │   │
│  │  1. Read checkpoint  2. Fetch data               │   │
│  │  3. Detect changes   4. Score + explain          │   │
│  │  5. Update checkpoint                            │   │
│  └────────────┬─────────────────────────────────────┘   │
│               │                                         │
│  ┌────────────▼─────────────────────────────────────┐   │
│  │           MarketDataService (cache layer)         │   │
│  │  Check StockSnapshot (< TTL) → return cached     │   │
│  │  Cache miss → call provider → save → return      │   │
│  └────────────┬─────────────────────────────────────┘   │
│               │                                         │
│  ┌────────────▼─────────────────────────────────────┐   │
│  │         Provider Layer (app/providers/)           │   │
│  │                                                   │   │
│  │  YahooFinanceProvider  ←  MARKET_DATA_PROVIDER=yahoo │
│  │  DemoProvider          ←  MARKET_DATA_PROVIDER=demo  │
│  │  (DemoProvider is always the fallback)            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  Database: SQLite (dev) · PostgreSQL (prod)             │
└─────────────────────────────────────────────────────────┘
```

### Provider architecture

```
BaseMarketProvider (abstract)
├── YahooFinanceProvider   — real data via yfinance
└── DemoProvider           — offline seeded scenarios

symbol_map.py              — single source of truth for ticker ↔ Yahoo symbol
                             TCS → TCS.NS, RELIANCE → RELIANCE.NS, AAPL → AAPL
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt |
| Market data | yfinance (free, no API key needed) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Testing | pytest, pytest-asyncio, unittest.mock |

---

## Local setup

### Prerequisites

- Python 3.11 or 3.12
- Node.js 18+
- Git

### 1. Clone

```bash
git clone https://github.com/IsHa2507/MarketWatchlist.git
cd MarketWatchlist/marketpulse
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example .env
# Edit .env — see Environment variables section below

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The database tables are created automatically on first startup.  
Schema migrations (new columns) are applied automatically via `run_migrations()`.

### 3. Frontend

```bash
cd frontend

npm install
npm run dev
```

Open http://localhost:5173

### 4. Register and log in

Go to http://localhost:5173/register and create an account.  
Or use the quick-login page at http://localhost:5173/quick-login if a demo user was seeded.

---

## Environment variables

Copy `.env.example` to `backend/.env` and edit as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./marketpulse.db` | Database connection string |
| `JWT_SECRET` | *(change in prod)* | Secret key for JWT signing |
| `JWT_EXPIRE_MINUTES` | `10080` | Token expiry (7 days) |
| `MARKET_DATA_PROVIDER` | `demo` | `yahoo` for real data, `demo` for offline |
| `MARKET_CACHE_TTL_SECONDS` | `300` | How long to cache a stock snapshot (seconds) |
| `NEWS_API_KEY` | *(empty)* | Optional — newsapi.org free tier (100 req/day) |
| `LLM_API_KEY` | *(empty)* | Optional — OpenAI key for AI explanations |
| `LLM_PROVIDER` | `openai` | LLM backend (`openai` or compatible) |
| `DEMO_MODE` | `true` | Legacy flag — use `MARKET_DATA_PROVIDER` instead |

**None of the optional keys are required.** The app works fully in demo mode with no external services.

---

## Demo mode

Demo mode uses deterministic, pre-seeded market scenarios.  
It works completely offline with no API keys or internet access.

```bash
# backend/.env
MARKET_DATA_PROVIDER=demo
```

Demo scenarios:
- **TCS** — significant price decline (−3.8%), high volume (2.1×) → IMPORTANT
- **NVDA** — strong surge (+6.2%), very high volume (2.8×) → CRITICAL
- **RELIANCE** — moderate gain (+2.4%), elevated volume → WORTH WATCHING
- **INFY** — minimal movement (+0.3%), normal volume → NORMAL
- Others — mix of normal to low-signal scenarios

The UI shows a **Demo** pill on every stock card when demo mode is active.

---

## Real market data mode

```bash
# backend/.env
MARKET_DATA_PROVIDER=yahoo
MARKET_CACHE_TTL_SECONDS=300
```

### Supported symbols

**Indian (NSE):**

| App ticker | Yahoo symbol | Company |
|-----------|-------------|---------|
| `TCS` | `TCS.NS` | Tata Consultancy Services |
| `RELIANCE` | `RELIANCE.NS` | Reliance Industries |
| `INFY` | `INFY.NS` | Infosys |
| `HDFCBANK` | `HDFCBANK.NS` | HDFC Bank |
| `ICICIBANK` | `ICICIBANK.NS` | ICICI Bank |
| `WIPRO` | `WIPRO.NS` | Wipro |
| `AXISBANK` | `AXISBANK.NS` | Axis Bank |

**US:**

| App ticker | Yahoo symbol | Company |
|-----------|-------------|---------|
| `AAPL` | `AAPL` | Apple |
| `NVDA` | `NVDA` | NVIDIA |
| `TSLA` | `TSLA` | Tesla |
| `MSFT` | `MSFT` | Microsoft |
| `AMZN` | `AMZN` | Amazon |
| `GOOGL` | `GOOGL` | Alphabet |
| `META` | `META` | Meta Platforms |

Symbol mapping lives entirely in `backend/app/providers/symbol_map.py`. Add new tickers there.

### Caching behaviour

To avoid hammering Yahoo Finance on every page load, all quotes are cached in the `stock_snapshots` database table.

```
First request for TCS
    → cache miss → fetch from Yahoo Finance → save to DB → return (FRESH)

Second request within 5 min
    → cache hit → return from DB (Cache label shown)

After 5 min
    → cache expired → fetch again → update DB → return (FRESH)
```

The frontend shows:
- 🟢 **Live** — fetched within TTL
- 🟡 **N min ago** — older than TTL but still available
- ⚪ **Market closed** — Yahoo reports CLOSED or POST state
- 🔴 **No data** — fetch failed, no snapshot available

### Important limitations of yfinance

1. **Not exchange-grade real-time.** Yahoo Finance data is typically delayed 15–20 min for US stocks and ~10 min for NSE. This is clearly shown in the UI with "Market data may be delayed depending on source."

2. **Unofficial API.** yfinance reverse-engineers Yahoo Finance's endpoints. It may break if Yahoo changes its API. The app falls back to demo mode automatically if yfinance fails.

3. **Rate limits.** Yahoo Finance has undocumented rate limits. The 5-minute cache prevents excessive requests. Do not set `MARKET_CACHE_TTL_SECONDS` below 60.

4. **No exchange-grade reliability.** Do not use MarketPulse for trading decisions. It is an informational tool only.

5. **Market hours.** Prices don't change when the market is closed. The UI clearly shows "Market closed" when `marketState` is `CLOSED` or `POST`.

---

## Attention Score

The Attention Score is a 0–100 explainable weighted signal calculated from 5 components:

| Component | Weight | Signal |
|-----------|--------|--------|
| Price movement | 35% | Absolute % change since checkpoint |
| Volume anomaly | 20% | Current volume vs average volume |
| News / sentiment | 20% | Sentiment magnitude + direction change |
| Volatility change | 15% | % change in volatility |
| Technical signal | 10% | Combined price + volume confirmation |

**Classification thresholds:**

| Range | Label |
|-------|-------|
| 0–30 | 🟢 NORMAL |
| 31–60 | 🟡 WORTH WATCHING |
| 61–80 | 🟠 IMPORTANT |
| 81–100 | 🔴 CRITICAL |

The scoring logic is in `backend/app/services/attention_scoring.py` and is fully unit-tested.

---

## Checkpoint system

```
User opens dashboard
    │
    ▼
Read previous checkpoint from user_checkpoints table
    │
    ▼
Fetch current market data (via cache or provider)
    │
    ▼
Compare: current vs checkpoint
    price_change_pct = (current_price - checkpoint_price) / checkpoint_price * 100
    volume_change_pct, volatility_change_pct, sentiment_change ...
    │
    ▼
Calculate Attention Score + classification
    │
    ▼
Generate explanation (template or LLM)
    │
    ▼
Render dashboard (sorted by attention score descending)
    │
    ▼
Save new checkpoint  ← ONLY AFTER comparison is complete
```

On first visit there is no checkpoint. `is_first_visit=true` is returned and the dashboard shows an informational message.

---

## Partial failure handling

If a watchlist contains TCS, RELIANCE, AAPL, and NVDA and NVDA's data fetch fails:

- TCS, RELIANCE, AAPL are shown normally
- NVDA appears in the `errors` array
- `partial_results: true` is set in the response
- The frontend shows a dismissible warning banner
- **The dashboard never returns a 500 error because one stock failed**

---

## Running tests

```bash
cd backend
python3 -m pytest tests/ -v
```

**101 tests** across 4 files:

| File | Tests | What it covers |
|------|-------|---------------|
| `test_attention.py` | 10 | Attention scoring, classification, scenarios |
| `test_auth.py` | 8 | Register, login, JWT, me endpoint |
| `test_watchlist.py` | 8 | CRUD, add/remove stocks, duplicate/invalid ticker |
| `test_providers.py` | 75 | Symbol map, freshness, DemoProvider, YahooFinanceProvider (mocked), cache, partial failure, provider interface |

All yfinance calls are mocked — tests pass with no internet connection.

```bash
# Run a specific group
python3 -m pytest tests/test_providers.py -v

# Run with coverage (requires pytest-cov)
python3 -m pytest tests/ --cov=app --cov-report=term-missing
```

---

## Docker

Start the full stack (backend + PostgreSQL + frontend):

```bash
cd marketpulse
docker-compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

To use real market data with Docker:

```yaml
# docker-compose.yml → backend → environment
MARKET_DATA_PROVIDER: "yahoo"
MARKET_CACHE_TTL_SECONDS: "300"
```

---

## API overview

```
POST   /auth/register
POST   /auth/login
GET    /auth/me

GET    /watchlists
POST   /watchlists
GET    /watchlists/{id}
PUT    /watchlists/{id}
DELETE /watchlists/{id}
POST   /watchlists/{id}/stocks
DELETE /watchlists/{id}/stocks/{ticker}

GET    /stocks/search?q=tcs
GET    /stocks/{ticker}
GET    /stocks/{ticker}/history?days=30
GET    /stocks/{ticker}/events

GET    /dashboard?watchlist_id=1
GET    /dashboard/changes
GET    /dashboard/attention

GET    /health
```

Full interactive docs: http://localhost:8000/docs

---

## Design decisions

**Why yfinance?**  
It is free, requires no API key, and supports both Indian NSE and US stocks. The unofficial nature is a known risk — the provider abstraction means it can be swapped for a paid provider (Polygon, Finnhub, Alpha Vantage) by adding a new provider class without changing any other code.

**Why SQLite for local dev?**  
No Docker required for development. The same code runs on PostgreSQL in production — `database.py` handles both.

**Why not WebSockets for real-time?**  
WebSockets don't magically make market data real-time — the data source (yfinance) is already delayed. The 5-minute cache + manual refresh is honest about the data's freshness and avoids unnecessary complexity.

**Why no AI dependency?**  
`ExplanationService` uses a template fallback when no LLM key is present. The application must never fail because AI is unavailable. LLM explanations are a progressive enhancement.

**Why is checkpoint read before update?**  
If the checkpoint were updated first, the "since you last checked" comparison would always show zero change. The correct order is: read → compare → score → display → update.

---

## Known limitations

1. **Delayed data** — yfinance data is not exchange-grade real-time. Always shown in UI.
2. **14 supported tickers** — adding more requires an entry in `symbol_map.py`. Dynamic ticker discovery is a future improvement.
3. **No live WebSocket push** — prices update on page load and manual refresh.
4. **Sentiment is neutral without NewsAPI** — the news layer is optional; scores still work without it.
5. **yfinance may break** — if Yahoo changes its internal API, the provider falls back to demo mode automatically.
6. **Single-user checkpoints** — checkpoints are per-user, but there is no concept of shared watchlists.

---

## Future improvements

- [ ] NewsAPI / RSS integration for real sentiment
- [ ] Ollama local LLM for offline AI explanations
- [ ] APScheduler background refresh (pre-warm cache every 5 min)
- [ ] WebSocket push when background refresh completes
- [ ] More tickers via dynamic yfinance search
- [ ] Alembic migrations for production schema management
- [ ] Portfolio-level P&L tracking
- [ ] Email / push alerts when Attention Score crosses threshold

---

## Important disclaimer

MarketPulse AI is an informational tool for educational and personal use.

It does **not** provide financial advice. It does **not** recommend buying or selling any security. Market data may be delayed and is provided as-is without warranty.

Always consult a qualified financial advisor before making investment decisions.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/IsHa2507/MarketWatchlist).

---

## License

MIT License - see LICENSE file for details.

---

## Links

- **GitHub Repository**: https://github.com/IsHa2507/MarketWatchlist
- **Live Demo**: Coming soon on Vercel
- **Issues & Feature Requests**: https://github.com/IsHa2507/MarketWatchlist/issues

---

## Project structure

```
marketpulse/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # FastAPI route handlers
│   │   ├── core/               # Config, security (JWT, bcrypt)
│   │   ├── db/                 # SQLAlchemy engine, migrations
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── providers/          # Market data provider layer
│   │   │   ├── base.py         # Abstract interface + FreshnessStatus
│   │   │   ├── symbol_map.py   # Ticker ↔ Yahoo symbol registry
│   │   │   ├── demo.py         # DemoProvider (offline)
│   │   │   └── yahoo_finance.py # YahooFinanceProvider
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── services/           # Business logic
│   │       ├── market_data.py      # Cache layer + provider selection
│   │       ├── change_detection.py # Checkpoint comparison
│   │       ├── attention_scoring.py # 0–100 weighted score
│   │       ├── explanation.py      # Template + LLM explanations
│   │       └── dashboard.py        # Orchestrator
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_attention.py
│   │   ├── test_auth.py
│   │   ├── test_watchlist.py
│   │   └── test_providers.py   # New: 75 provider/cache/freshness tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/      # AttentionCard, WatchingCard, NormalSection
│   │   │   ├── stock/          # Detail page sub-components
│   │   │   └── ui/             # Badge, Alert, FreshnessBadge, Skeleton
│   │   ├── pages/              # DashboardPage, StockDetailPage, etc.
│   │   ├── services/api.ts     # Axios API client
│   │   └── types/index.ts      # TypeScript interfaces
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```
