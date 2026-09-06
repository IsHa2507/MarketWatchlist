# MarketPulse Production Implementation Guide

## 🚨 Current Status: DEMO MODE
The application currently uses **seeded/fake data**. This is NOT real-time.

---

## 📊 Real-Time Implementation Roadmap

### Step 1: Choose Market Data Provider

#### Option A: Indian Stocks (NSE/BSE)
```python
# Recommended: Alpha Vantage (Free tier available)
# https://www.alphavantage.co/

import requests

def get_live_quote(symbol: str):
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": f"{symbol}.BSE",  # For Indian stocks
        "apikey": "YOUR_API_KEY"
    }
    response = requests.get(url, params=params)
    return response.json()
```

**Other Options:**
- **NSEpy** (Python library for NSE data) - Free but unofficial
- **Upstox API** - Official, requires broker account
- **Zerodha Kite Connect** - ₹2000/month
- **TrueData** - Professional grade
- **IEX Cloud** - For US stocks

#### Option B: US Stocks
- **Alpha Vantage** - 5 calls/min free, 75 calls/min paid ($49/month)
- **Finnhub** - 60 calls/min free
- **Polygon.io** - $29/month for real-time
- **Yahoo Finance API** (via `yfinance` library) - Free but rate-limited

---

### Step 2: Update MarketDataService

Replace the demo implementation:

```python
# backend/app/services/market_data.py

import os
import requests
from functools import lru_cache

class MarketDataService:
    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv("MARKET_API_KEY")
        self.demo_mode = not self.api_key  # Auto-detect
        
        if self.demo_mode:
            print("⚠️  Running in DEMO MODE - using fake data")
        else:
            print("✓ Live market data enabled")

    def get_stock(self, ticker: str) -> Optional[Dict[str, Any]]:
        if self.demo_mode:
            return self._get_demo_stock(ticker)
        else:
            return self._get_live_stock(ticker)
    
    def _get_live_stock(self, ticker: str) -> Dict[str, Any]:
        """Fetch real-time data from API"""
        # Example: Alpha Vantage
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": self.api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        quote = data.get("Global Quote", {})
        
        return {
            "ticker": ticker,
            "company_name": self._get_company_name(ticker),
            "price": float(quote.get("05. price", 0)),
            "price_change": float(quote.get("09. change", 0)),
            "price_change_percent": float(quote.get("10. change percent", "0").rstrip("%")),
            "volume": int(quote.get("06. volume", 0)),
            "last_updated": datetime.utcnow(),
            "data_confidence": "HIGH",
            "demo_mode": False,
        }
```

---

### Step 3: WebSocket for Real-Time Updates

For true real-time (price updates every second), use WebSockets:

```python
# backend/app/websockets/market_stream.py

import asyncio
import websockets
import json
from fastapi import WebSocket

class MarketStreamManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscribed_tickers: Set[str] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def stream_prices(self):
        """Background task to fetch and broadcast prices"""
        while True:
            for ticker in self.subscribed_tickers:
                # Fetch latest price
                price_data = await self.fetch_live_price(ticker)
                
                # Broadcast to all connected clients
                await self.broadcast({
                    "type": "price_update",
                    "ticker": ticker,
                    "data": price_data
                })
            
            await asyncio.sleep(1)  # Update every second

# In main.py
from fastapi import WebSocket, WebSocketDisconnect

manager = MarketStreamManager()

@app.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle subscribe/unsubscribe
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
```

**Frontend WebSocket Client:**
```typescript
// frontend/src/hooks/useMarketStream.ts

export function useMarketStream(tickers: string[]) {
  const [prices, setPrices] = useState<Record<string, number>>({})
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/market')
    
    ws.onopen = () => {
      // Subscribe to tickers
      ws.send(JSON.stringify({ action: 'subscribe', tickers }))
    }
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data)
      if (update.type === 'price_update') {
        setPrices(prev => ({
          ...prev,
          [update.ticker]: update.data.price
        }))
      }
    }
    
    return () => ws.close()
  }, [tickers])
  
  return prices
}
```

---

### Step 4: News & Events Integration

```python
# backend/app/services/news_service.py

import requests

class NewsService:
    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY")
        self.base_url = "https://newsapi.org/v2"
    
    def fetch_stock_news(self, ticker: str, days: int = 7):
        """Fetch real news from NewsAPI"""
        url = f"{self.base_url}/everything"
        params = {
            "q": ticker,
            "apiKey": self.api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10
        }
        
        response = requests.get(url, params=params)
        articles = response.json().get("articles", [])
        
        # Convert to MarketEvent format
        events = []
        for article in articles:
            # Use AI to analyze sentiment
            sentiment = self._analyze_sentiment(article["title"])
            
            event = MarketEvent(
                ticker=ticker,
                event_type="news",
                title=article["title"],
                description=article["description"],
                sentiment=sentiment,
                impact_score=self._calculate_impact(article),
                source=article["source"]["name"],
                timestamp=article["publishedAt"]
            )
            events.append(event)
        
        return events
```

---

### Step 5: Sentiment Analysis (AI Integration)

```python
# backend/app/services/sentiment_analyzer.py

from openai import OpenAI

class SentimentAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("LLM_API_KEY"))
    
    def analyze_news_sentiment(self, title: str, description: str) -> tuple[str, float]:
        """
        Returns: (sentiment_label, sentiment_score)
        sentiment_label: 'positive', 'negative', 'neutral'
        sentiment_score: -1.0 to +1.0
        """
        prompt = f"""
        Analyze the sentiment of this stock market news.
        
        Title: {title}
        Description: {description}
        
        Respond with JSON:
        {{
            "sentiment": "positive|negative|neutral",
            "score": <-1.0 to +1.0>,
            "reasoning": "<brief explanation>"
        }}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result["sentiment"], result["score"]
```

---

### Step 6: Background Jobs (APScheduler)

```python
# backend/app/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.market_data import MarketDataService
from app.services.news_service import NewsService

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=5)
async def update_stock_prices():
    """Update prices every 5 minutes"""
    db = SessionLocal()
    market_svc = MarketDataService(db)
    
    # Get all tracked tickers
    tickers = get_all_tracked_tickers(db)
    
    for ticker in tickers:
        quote = market_svc.get_stock(ticker)
        
        # Save snapshot
        snapshot = StockSnapshot(
            ticker=ticker,
            price=quote["price"],
            volume=quote["volume"],
            timestamp=datetime.utcnow()
        )
        db.add(snapshot)
    
    db.commit()
    db.close()

@scheduler.scheduled_job('interval', hours=1)
async def fetch_news():
    """Fetch news every hour"""
    db = SessionLocal()
    news_svc = NewsService()
    
    tickers = get_all_tracked_tickers(db)
    
    for ticker in tickers:
        events = news_svc.fetch_stock_news(ticker)
        for event in events:
            db.add(event)
    
    db.commit()
    db.close()

# In main.py
@app.on_event("startup")
def start_scheduler():
    scheduler.start()
```

---

### Step 7: Caching Layer (Redis)

```python
# backend/app/cache.py

import redis
import json
from datetime import timedelta

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    decode_responses=True
)

def cache_quote(ticker: str, data: dict, ttl_seconds: int = 60):
    """Cache stock quote for 1 minute"""
    key = f"quote:{ticker}"
    redis_client.setex(key, ttl_seconds, json.dumps(data))

def get_cached_quote(ticker: str) -> Optional[dict]:
    """Get cached quote"""
    key = f"quote:{ticker}"
    cached = redis_client.get(key)
    return json.loads(cached) if cached else None

# Usage in MarketDataService
def get_stock(self, ticker: str):
    # Try cache first
    cached = get_cached_quote(ticker)
    if cached:
        return cached
    
    # Fetch from API
    quote = self._fetch_from_api(ticker)
    
    # Cache it
    cache_quote(ticker, quote, ttl_seconds=60)
    
    return quote
```

---

## 🏗️ Infrastructure Requirements

### Docker Compose for Production

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: marketpulse
      POSTGRES_USER: marketpulse
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7-alpine
    restart: always

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://marketpulse:${DB_PASSWORD}@postgres:5432/marketpulse
      REDIS_URL: redis://redis:6379
      MARKET_API_KEY: ${MARKET_API_KEY}
      NEWS_API_KEY: ${NEWS_API_KEY}
      LLM_API_KEY: ${LLM_API_KEY}
    depends_on:
      - postgres
      - redis
    restart: always

  frontend:
    build: ./frontend
    environment:
      VITE_API_URL: https://api.yourdomain.com
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    restart: always

volumes:
  postgres_data:
```

---

## 💰 Cost Estimate (Monthly)

| Service | Free Tier | Paid Plan |
|---------|-----------|-----------|
| **Alpha Vantage API** | 5 calls/min | $49/mo (75 calls/min) |
| **NewsAPI** | 100 requests/day | $449/mo (unlimited) |
| **OpenAI GPT-4o-mini** | - | ~$5-20/mo (for explanations) |
| **Redis Cloud** | 30MB free | $7/mo (250MB) |
| **PostgreSQL** (Supabase) | 500MB free | $25/mo (8GB) |
| **Hosting** (DigitalOcean) | - | $12/mo (2GB RAM) |
| **Total (Free tier)** | $0 | - |
| **Total (Production)** | - | ~$100-150/mo |

---

## 🚀 Deployment Checklist

- [ ] Sign up for Alpha Vantage API key
- [ ] Sign up for NewsAPI key  
- [ ] Sign up for OpenAI API key
- [ ] Set up PostgreSQL (production)
- [ ] Set up Redis (optional but recommended)
- [ ] Configure environment variables
- [ ] Update `DEMO_MODE=false` in backend
- [ ] Deploy to cloud (AWS/DigitalOcean/Railway)
- [ ] Set up domain & SSL certificate
- [ ] Configure rate limiting & caching
- [ ] Set up monitoring (Sentry/DataDog)
- [ ] Schedule background jobs
- [ ] Test with real API calls

---

## 📝 Environment Variables Needed

```bash
# .env.production
DATABASE_URL=postgresql://user:pass@host:5432/marketpulse
REDIS_URL=redis://host:6379

# Market Data
MARKET_API_KEY=your_alpha_vantage_key
NEWS_API_KEY=your_newsapi_key

# AI
LLM_API_KEY=sk-...your_openai_key
LLM_PROVIDER=openai

# App
ENVIRONMENT=production
DEMO_MODE=false
JWT_SECRET=super-secure-secret-change-this

# Frontend
VITE_API_URL=https://api.yourdomain.com
```

---

## 🎯 Summary

**Current:** Demo mode with fake data  
**Production:** Need real APIs + background jobs + caching + infrastructure

**Next Steps:**
1. Register for Alpha Vantage API (free tier to start)
2. Test with 5 stocks first (within free limits)
3. Implement caching to reduce API calls
4. Add background scheduler
5. Scale up with paid plan when ready

---

## 🔗 Useful Resources

- Alpha Vantage Docs: https://www.alphavantage.co/documentation/
- NSEpy (Python): https://github.com/vsjha18/nsedt
- Finnhub API: https://finnhub.io/docs/api
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- APScheduler Docs: https://apscheduler.readthedocs.io/
