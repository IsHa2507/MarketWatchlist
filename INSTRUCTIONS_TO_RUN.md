# 🚀 Instructions to Run - MarketPulse AI

Quick setup guide for reviewers to test the project locally.

---

## Prerequisites

- **Python 3.11+** (check: `python3 --version`)
- **Node.js 18+** (check: `node --version`)
- **Git**

---

## Quick Start (5 minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/IsHa2507/MarketWatchlist.git
cd MarketWatchlist/marketpulse
```

### Step 2: Set Up Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate it (choose your OS)
source .venv/bin/activate           # Mac/Linux
# OR
.venv\Scripts\activate              # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file (uses demo mode by default)
cp ../.env.example .env

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend running at: **http://localhost:8000**  
✅ API docs at: **http://localhost:8000/docs**

### Step 3: Set Up Frontend (in a new terminal)

```bash
cd MarketWatchlist/marketpulse/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

✅ Frontend running at: **http://localhost:5173**

### Step 4: Open the App

Open your browser to: **http://localhost:5173**

🎉 **You're in!** The app loads directly to the dashboard (no login required for demo).

---

## What to Test

### 1. Dashboard (Main Feature)
- **URL**: http://localhost:5173/dashboard
- View stocks categorized by attention level:
  - 🔴 **Needs Attention** (critical changes)
  - 🟡 **Worth Watching** (moderate changes)
  - 🟢 **Nothing Significant** (stable stocks)
- Each stock shows:
  - Current price and change %
  - Attention Score (0-100)
  - Why it matters (AI explanation)
  - Volume multiplier
  - Freshness indicator

### 2. Stock Detail Page
- Click any stock card to see:
  - Price history chart (interactive)
  - Volume chart
  - Attention score breakdown
  - Key reasons for the score
  - News & events
- Try different time ranges (7D, 14D, 30D, 90D)

### 3. Watchlist Management
- Click "+" to create a new watchlist
- Add stocks (search works)
- Rename/delete watchlists
- Switch between watchlists

### 4. Search Feature
- Use search bar in header
- Try: "TCS", "NVIDIA", "Apple", "Reliance"
- Search works for both ticker and company name

### 5. Demo Mode Features
The app runs in **demo mode** by default (no API keys needed):
- ✅ Works completely offline
- ✅ Pre-seeded realistic scenarios:
  - **TCS**: Declining (Important)
  - **NVDA**: Surging (Critical)
  - **RELIANCE**: Moderate gain (Worth Watching)
  - **AAPL**, **AMZN**, etc.: Stable

---

## Optional: Test with Real Market Data

Want to see live prices from Yahoo Finance?

1. Edit `backend/.env`:
   ```bash
   MARKET_DATA_PROVIDER=yahoo
   MARKET_CACHE_TTL_SECONDS=300
   ```

2. Restart the backend:
   ```bash
   # Stop the server (Ctrl+C), then:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Refresh the dashboard - now using real data!

**Note**: Yahoo Finance data is delayed 15-20 minutes. This is clearly shown in the UI.

---

## Run Tests

```bash
cd backend

# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_attention.py -v

# Run with coverage
python3 -m pytest tests/ --cov=app --cov-report=term-missing
```

**187 tests** should pass ✅

---

## Docker (Alternative)

If you prefer Docker:

```bash
cd MarketWatchlist/marketpulse

# Start everything
docker-compose up --build

# Access:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
# - API docs: http://localhost:8000/docs
```

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Try recreating venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend won't start
```bash
# Clear and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Port already in use
```bash
# Backend on different port
uvicorn app.main:app --reload --port 8001

# Update frontend to match
# Edit frontend/.env or frontend/vite.config.ts
```

### Database issues
```bash
# Delete and recreate
cd backend
rm marketpulse.db
# Restart server - tables auto-create
```

---

## Key Files to Review

### Backend Architecture
- `backend/app/services/dashboard.py` - Main orchestrator
- `backend/app/services/attention_scoring.py` - AI scoring logic
- `backend/app/providers/` - Market data abstraction
- `backend/tests/` - Comprehensive test suite

### Frontend Architecture
- `frontend/src/pages/DashboardPage.tsx` - Main dashboard
- `frontend/src/components/dashboard/` - Dashboard components
- `frontend/src/services/api.ts` - API client
- `frontend/src/types/index.ts` - TypeScript interfaces

---

## Demo Credentials (Optional)

The app works without login in demo mode. If you want to test authentication:

**Register**: http://localhost:5173/register
- Email: `test@example.com`
- Password: `password123`

Or the demo user may already exist:
- Email: `demo@marketpulse.app`
- Password: `demo123`

---

## API Endpoints (for testing)

Visit **http://localhost:8000/docs** for interactive API documentation.

Key endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Get dashboard
curl http://localhost:8000/dashboard

# Search stocks
curl "http://localhost:8000/stocks/search?q=tesla"

# Get stock detail
curl http://localhost:8000/stocks/NVDA

# List watchlists
curl http://localhost:8000/watchlists
```

---

## Environment Variables (Reference)

Default `.env` settings (works out of the box):

```bash
DATABASE_URL=sqlite:///./marketpulse.db
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRE_MINUTES=10080
MARKET_DATA_PROVIDER=demo
MARKET_CACHE_TTL_SECONDS=300
DEMO_MODE=true
```

Optional (for advanced features):
```bash
NEWS_API_KEY=           # newsapi.org free tier
LLM_API_KEY=            # OpenAI for AI explanations
LLM_PROVIDER=openai
```

---

## Expected Behavior

### First Load
- Dashboard shows 4 demo stocks (TCS, AMZN, AAPL, HDFCBANK)
- Message: "This is your first visit..."
- All stocks appear in "Nothing Significant" (no baseline yet)

### Second Load (after refresh)
- Stocks now categorized by change
- Attention scores visible
- AI explanations shown
- "Since you last checked..." comparisons work

### Demo Mode Indicators
- Every stock card shows "Demo" badge
- Freshness shows "🟢 Live" (simulated)
- Charts populated with realistic data

---

## Performance

- Backend startup: ~2 seconds
- Frontend build: ~4 seconds
- Dashboard load: ~200-300ms (demo mode)
- Dashboard load: ~1-2s (Yahoo Finance with cache miss)

---

## Support

- **Issues**: https://github.com/IsHa2507/MarketWatchlist/issues
- **Documentation**: See `README.md` for detailed architecture
- **Deployment**: See `RENDER_DEPLOYMENT.md` for production setup

---

## Summary

```bash
# Quick copy-paste to get started:

git clone https://github.com/IsHa2507/MarketWatchlist.git
cd MarketWatchlist/marketpulse

# Terminal 1 (Backend)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 (Frontend)
cd frontend
npm install
npm run dev

# Open: http://localhost:5173
```

🎉 **That's it!** The app should be running and ready to test.
