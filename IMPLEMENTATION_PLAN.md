# MarketPulse: Demo → Production MVP Implementation Plan

## 📋 Current Architecture Analysis

### ✅ What Already Works (Preserve These)

**Backend:**
- ✅ FastAPI with SQLAlchemy ORM
- ✅ JWT authentication (bcrypt)
- ✅ User, Watchlist, WatchlistStock models
- ✅ StockSnapshot, MarketEvent, UserCheckpoint models
- ✅ **Checkpoint-based change detection** (correct order: read → compare → update)
- ✅ AttentionScoringService (5-component weighted: 35% price, 20% volume, 20% sentiment, 15% volatility, 10% technical)
- ✅ Classification (CRITICAL/IMPORTANT/WORTH_WATCHING/NORMAL)
- ✅ ExplanationService with LLM + template fallback
- ✅ DashboardService orchestrating the full pipeline
- ✅ Demo mode with deterministic scenarios
- ✅ 26 passing tests including checkpoint ordering

**Frontend:**
- ✅ React 18 + TypeScript + Vite
- ✅ Tailwind CSS dark theme
- ✅ Auth context with JWT
- ✅ Dashboard with "Since You Last Checked" UI
- ✅ Stock cards with attention scores
- ✅ Stock detail page with charts (Recharts)
- ✅ Watchlist management
- ✅ Search functionality
- ✅ Responsive design

**Database:**
- ✅ SQLite for local dev (currently)
- ✅ All necessary models defined
- ✅ Proper relationships

### 🔴 What Needs to Change (Demo → Real)

**CRITICAL ISSUE:**
Current `market_data.py` has:
- ❌ Hardcoded `COMPANY_METADATA` with `base_price`
- ❌ Hardcoded `DEMO_SCENARIOS` with predetermined changes
- ❌ `_get_demo_stock()` generates fake data
- ❌ `_get_demo_history()` uses seeded random walk
- ❌ No real market data provider
- ❌ No caching/storage of real market data
- ❌ No freshness tracking
- ❌ No error handling for API failures
- ❌ No support for market closed state

**WHAT USERS NEED:**
- ✅ Real market prices from yfinance
- ✅ Indian NSE symbols (TCS.NS, RELIANCE.NS, etc.)
- ✅ US symbols (AAPL, NVDA, etc.)
- ✅ Actual historical data
- ✅ Data freshness indicators
- ✅ Graceful degradation when APIs fail
- ✅ Demo mode as fallback (keep existing)

---

## 🎯 Implementation Strategy

### Phase 1: Provider Abstraction (Foundation)

**Goal:** Create clean architecture that supports multiple providers

**Files to Create:**
```
backend/app/providers/
├── __init__.py
├── base.py              # Abstract base class
├── yahoo_finance.py     # YahooFinanceProvider
└── demo.py              # DemoProvider (move existing logic)
```

**Implementation:**
1. Create `BaseMarketProvider` abstract class
2. Move existing demo logic to `DemoProvider`
3. Implement `YahooFinanceProvider` using yfinance
4. Update `MarketDataService` to use provider pattern

**Key Interfaces:**
```python
class BaseMarketProvider(ABC):
    @abstractmethod
    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]
    
    @abstractmethod
    def get_history(self, ticker: str, days: int) -> List[Dict[str, Any]]
    
    @abstractmethod
    def search_stocks(self, query: str) -> List[Dict[str, Any]]
    
    @abstractmethod
    def is_available(self) -> bool
```

---

### Phase 2: Yahoo Finance Integration

**Dependencies:**
```bash
pip install yfinance
```

**Symbol Mapping:**
| User Input | Yahoo Symbol |
|------------|--------------|
| TCS | TCS.NS |
| RELIANCE | RELIANCE.NS |
| INFY | INFY.NS |
| HDFCBANK | HDFCBANK.NS |
| ICICIBANK | ICICIBANK.NS |
| AAPL | AAPL |
| NVDA | NVDA |
| TSLA | TSLA |
| MSFT | MSFT |
| AMZN | AMZN |

**Implementation:**
```python
import yfinance as yf

class YahooFinanceProvider(BaseMarketProvider):
    def __init__(self):
        self.symbol_map = {
            "TCS": "TCS.NS",
            "RELIANCE": "RELIANCE.NS",
            # ... etc
        }
    
    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            yahoo_symbol = self._normalize_symbol(ticker)
            stock = yf.Ticker(yahoo_symbol)
            info = stock.info
            history = stock.history(period="2d")
            
            return {
                "ticker": ticker,
                "company_name": info.get("longName", ticker),
                "sector": info.get("sector", "Unknown"),
                "currency": info.get("currency", "USD"),
                "price": info.get("currentPrice"),
                "previous_close": info.get("previousClose"),
                "price_change_percent": ...,
                "volume": info.get("volume"),
                "average_volume": info.get("averageVolume"),
                "volatility": self._calculate_volatility(history),
                "market_state": info.get("marketState"),  # PRE, REGULAR, POST, CLOSED
                "last_updated": datetime.utcnow(),
                "data_source": "Yahoo Finance",
                "data_timestamp": ...,
                "demo_mode": False,
            }
        except Exception as e:
            logger.error(f"YahooFinance failed for {ticker}: {e}")
            return None
```

---

### Phase 3: Data Persistence & Caching

**Goal:** Don't call Yahoo Finance on every dashboard refresh

**Strategy:**
```
Frontend Request
↓
MarketDataService.get_stock(ticker)
↓
Check StockSnapshot table (< 5 min old?)
├─ YES → Return cached data
└─ NO  → Fetch from provider → Save to DB → Return
```

**Update `stock_snapshots` table:**
```python
class StockSnapshot(Base):
    # ... existing fields ...
    data_source = Column(String, default="demo")  # NEW
    data_timestamp = Column(DateTime)  # NEW: when market data was generated
    fetched_at = Column(DateTime)     # NEW: when we fetched it
    is_stale = Column(Boolean, default=False)  # NEW
    error_message = Column(Text, nullable=True)  # NEW
```

**MarketDataService logic:**
```python
def get_stock(self, ticker: str) -> Optional[Dict[str, Any]]:
    # 1. Check cache
    cached = self._get_cached_snapshot(ticker, max_age_seconds=300)
    if cached:
        return cached
    
    # 2. Try live provider
    if not self.demo_mode:
        live_data = self.provider.get_quote(ticker)
        if live_data:
            self._save_snapshot(ticker, live_data)
            return live_data
    
    # 3. Fall back to demo
    return self._get_demo_stock(ticker)
```

---

### Phase 4: Sentiment Integration (Optional News)

**Goal:** Replace hardcoded sentiment with real news

**Strategy:**
- Use RSS feeds (free)
- Optional: NewsAPI (100 requests/day free)
- Fallback: neutral sentiment if unavailable

**Implementation:**
```python
class NewsService:
    def fetch_stock_news(self, ticker: str, days: int = 7):
        # Try NewsAPI
        if settings.NEWS_API_KEY:
            return self._fetch_from_newsapi(ticker)
        
        # Try RSS feeds
        rss_news = self._fetch_from_rss(ticker)
        if rss_news:
            return rss_news
        
        # Fallback: no news
        return []
```

**Sentiment calculation:**
- If LLM available: use OpenAI/Ollama to analyze headlines
- Otherwise: keyword-based heuristic
- Default: neutral (0.0)

---

### Phase 5: Data Freshness UI

**Add to every market data response:**
```python
{
    "ticker": "TCS",
    "price": 3650.0,
    # ... other fields ...
    "freshness": {
        "status": "FRESH",  # FRESH, STALE, VERY_STALE, ERROR
        "fetched_at": "2024-02-15T10:30:00Z",
        "age_seconds": 45,
        "data_source": "Yahoo Finance",
        "market_state": "CLOSED",
        "message": "Market closed — showing latest available data"
    }
}
```

**Frontend:**
```tsx
{freshness.status === 'FRESH' && <Badge>🟢 Live</Badge>}
{freshness.status === 'STALE' && <Badge>🟡 {freshness.age_minutes}m ago</Badge>}
{freshness.status === 'VERY_STALE' && <Badge>🔴 Stale</Badge>}
{freshness.market_state === 'CLOSED' && <Badge>Market Closed</Badge>}
```

---

### Phase 6: Error Handling & Partial Results

**Critical Rule:** Dashboard must NEVER crash because one stock failed

**Implementation:**
```python
def get_dashboard(self, user_id: int, watchlist_id: Optional[int] = None):
    tickers = [...]
    
    all_results = []
    failed_tickers = []
    
    for ticker in tickers:
        try:
            change_data = self.change_detector.detect_changes(user_id, ticker)
            if change_data:
                # ... calculate attention score ...
                all_results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {ticker}: {e}")
            failed_tickers.append({
                "ticker": ticker,
                "error": str(e)
            })
    
    return {
        # ... results ...
        "errors": failed_tickers,
        "partial_results": len(failed_tickers) > 0
    }
```

**Frontend:**
```tsx
{dashboard.partial_results && (
  <Alert>
    Some stocks couldn't be updated. Showing available data.
  </Alert>
)}
```

---

### Phase 7: Background Refresh (Optional)

**Goal:** Pre-fetch market data periodically

**Using APScheduler:**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('interval', minutes=5)
def refresh_tracked_stocks():
    db = SessionLocal()
    # Get all unique tickers from all watchlists
    tickers = get_all_tracked_tickers(db)
    
    for ticker in tickers:
        try:
            market_svc.get_stock(ticker)  # This will cache it
        except Exception as e:
            logger.error(f"Background refresh failed for {ticker}: {e}")
    
    db.close()

# In main.py
@app.on_event("startup")
def start_scheduler():
    if not settings.DEMO_MODE:
        scheduler.start()
```

---

### Phase 8: WebSocket Updates (Optional)

**Goal:** Push price updates to connected clients

**Implementation:**
```python
# main.py
from fastapi import WebSocket

active_connections: List[WebSocket] = []

@app.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(60)  # Every minute
            # Fetch latest prices
            # Broadcast to all connections
    except WebSocketDisconnect:
        active_connections.remove(websocket)
```

**Frontend:**
```typescript
const ws = new WebSocket('ws://localhost:8000/ws/market')

ws.onmessage = (event) => {
  const update = JSON.parse(event.data)
  // Update prices in state
}
```

---

## 📁 Files to Modify

### Backend

| File | Action | Complexity |
|------|--------|------------|
| `requirements.txt` | Add `yfinance` | Simple |
| `app/core/config.py` | Add `MARKET_DATA_PROVIDER` | Simple |
| `app/models/market.py` | Add freshness fields | Simple |
| `app/providers/__init__.py` | CREATE | Medium |
| `app/providers/base.py` | CREATE | Medium |
| `app/providers/yahoo_finance.py` | CREATE | Complex |
| `app/providers/demo.py` | MOVE existing logic | Medium |
| `app/services/market_data.py` | REFACTOR to use providers | Complex |
| `app/services/dashboard.py` | Add error handling | Medium |
| `app/api/routes/stocks.py` | Add freshness to responses | Simple |
| `tests/test_providers.py` | CREATE new tests | Medium |

### Frontend

| File | Action | Complexity |
|------|--------|------------|
| `src/types/market.ts` | Add freshness types | Simple |
| `src/components/StockCard.tsx` | Add freshness badge | Medium |
| `src/components/FreshnessBadge.tsx` | CREATE | Simple |
| `src/pages/Dashboard.tsx` | Handle partial results | Medium |

### Config

| File | Action |
|------|--------|
| `.env.example` | Add `MARKET_DATA_PROVIDER=yahoo` |
| `README.md` | Update with real data instructions |

---

## 🚀 Execution Order

### Step 1: Add yfinance dependency
```bash
cd backend
echo "yfinance==0.2.36" >> requirements.txt
pip install yfinance
```

### Step 2: Create provider abstraction
- Create `app/providers/` directory
- Implement `base.py`
- Move demo logic to `demo.py`
- Implement `yahoo_finance.py`

### Step 3: Update MarketDataService
- Refactor to use provider pattern
- Add caching logic
- Add error handling

### Step 4: Update database models
- Add migration for new snapshot fields
- Update StockSnapshot model

### Step 5: Update API responses
- Add freshness data to all stock endpoints

### Step 6: Update frontend
- Add freshness badges
- Handle partial results
- Show data source

### Step 7: Testing
- Run existing 26 tests (should still pass)
- Add provider tests
- Manual testing with real stocks

### Step 8: Documentation
- Update README
- Add production deployment guide
- Document known limitations

---

## ✅ Acceptance Criteria Checklist

### Core Functionality
- [ ] `MARKET_DATA_PROVIDER=yahoo` fetches real data from yfinance
- [ ] `MARKET_DATA_PROVIDER=demo` uses existing demo mode
- [ ] Indian stocks work (TCS.NS, RELIANCE.NS, etc.)
- [ ] US stocks work (AAPL, NVDA, etc.)
- [ ] Invalid tickers handled gracefully
- [ ] Market data is cached (< 5 min)
- [ ] Stale data is clearly marked

### Change Detection
- [ ] Checkpoint comparison still works correctly
- [ ] "Since You Last Checked" uses real price changes
- [ ] Attention Score calculated from real data
- [ ] First-time visits handled correctly

### Error Handling
- [ ] Dashboard doesn't crash if one stock fails
- [ ] Network errors handled gracefully
- [ ] Provider timeouts handled
- [ ] Partial results displayed correctly

### UI/UX
- [ ] Freshness badge shows data age
- [ ] Market closed state indicated
- [ ] Data source shown (Yahoo Finance / Demo)
- [ ] Loading states for data fetch
- [ ] Error messages are user-friendly

### Testing
- [ ] All 26 existing tests pass
- [ ] New provider tests pass
- [ ] Manual testing successful

### Documentation
- [ ] README updated
- [ ] Environment variables documented
- [ ] Known limitations listed
- [ ] Demo instructions still work

---

## 🎯 Known Limitations (To Document)

1. **Not Exchange-Grade Real-Time:**
   - Yahoo Finance data may be delayed 15-20 minutes
   - Clearly state: "Market data may be delayed"

2. **Free Tier Limits:**
   - yfinance has rate limits (undocumented)
   - Implement caching to reduce requests

3. **Market Hours:**
   - Prices don't update when market is closed
   - Show "Market closed" indicator

4. **Symbol Support:**
   - Only supports stocks in COMPANY_METADATA
   - Can't dynamically discover new stocks (yet)

5. **Sentiment:**
   - Without NEWS_API_KEY, sentiment is neutral
   - Explain this in UI if relevant

---

## 💰 Cost Analysis

| Component | Free Tier | Cost |
|-----------|-----------|------|
| **yfinance** | Unlimited (unofficial API) | ₹0 |
| **NewsAPI** | 100 requests/day | ₹0 |
| **OpenAI GPT-4o-mini** | Pay-per-use | ~₹200-500/mo |
| **Ollama** | Self-hosted | ₹0 |
| **Hosting** | Railway/Render free tier | ₹0-400/mo |
| **PostgreSQL** | Supabase free tier | ₹0 |
| **Total** | With free tiers | **₹0-900/mo** |

**Hackathon Demo:** Use demo mode + yfinance = ₹0

---

## 🏁 Next Steps After This Document

1. ✅ Review this plan with user
2. Get approval on approach
3. Start implementation Phase 1
4. Test each phase before proceeding
5. Keep existing tests passing
6. Update README continuously

---

**Estimated Implementation Time:** 6-8 hours
**Risk Level:** Low (preserves existing features)
**Breaking Changes:** None (demo mode still works)
