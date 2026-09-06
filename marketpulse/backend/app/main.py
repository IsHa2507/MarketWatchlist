from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, watchlists, stocks, dashboard
from app.core.config import settings

app = FastAPI(
    title="MarketPulse API",
    description="Smart stock market watchlist — watch less, understand more.",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(watchlists.router)
app.include_router(stocks.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def startup():
    import os
    if os.environ.get("TESTING") == "1":
        return
    from app.db.database import Base, engine, run_migrations
    Base.metadata.create_all(bind=engine)
    run_migrations()


@app.get("/")
def root():
    return {
        "app": "MarketPulse",
        "tagline": "Watch less. Understand more.",
        "version": "1.0.0",
        "demo_mode": settings.DEMO_MODE,
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
