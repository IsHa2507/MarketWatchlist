import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

_url = settings.DATABASE_URL

# SQLite needs different engine kwargs (no pool_size, check_same_thread=False)
if _url.startswith("sqlite"):
    engine = create_engine(
        _url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        _url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schema migration helper
# Adds new columns to existing tables without breaking existing data.
# Works for both SQLite (ALTER TABLE ADD COLUMN) and PostgreSQL.
# Called from main.py startup after Base.metadata.create_all().
# ---------------------------------------------------------------------------

_MIGRATIONS = [
    # (table, column_name, column_definition)
    # v2: freshness / provenance on stock_snapshots
    ("stock_snapshots", "data_source",              "VARCHAR DEFAULT 'Demo'"),
    ("stock_snapshots", "data_timestamp",            "DATETIME"),
    ("stock_snapshots", "fetched_at",               "DATETIME"),
    ("stock_snapshots", "freshness_status",          "VARCHAR DEFAULT 'FRESH'"),
    ("stock_snapshots", "is_stale",                  "BOOLEAN DEFAULT 0"),
    # v3 / Phase 2: sentiment provenance on stock_snapshots
    ("stock_snapshots", "sentiment_source",          "VARCHAR DEFAULT 'Unavailable'"),
    ("stock_snapshots", "sentiment_timestamp",       "DATETIME"),
    ("stock_snapshots", "sentiment_article_count",   "INTEGER DEFAULT 0"),
]


def run_migrations() -> None:
    """
    Add any missing columns to existing tables.
    Safe to run multiple times — skips columns that already exist.
    """
    inspector = inspect(engine)
    with engine.connect() as conn:
        for table, column, col_def in _MIGRATIONS:
            # Check if table exists at all
            if table not in inspector.get_table_names():
                continue
            existing_cols = [c["name"] for c in inspector.get_columns(table)]
            if column not in existing_cols:
                try:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                    )
                    conn.commit()
                    logger.info("Migration: added column '%s.%s'", table, column)
                except Exception as exc:
                    # Column may have been added by a concurrent process — safe to ignore
                    logger.debug(
                        "Migration skipped '%s.%s': %s", table, column, exc
                    )
