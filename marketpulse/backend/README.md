# MarketPulse Backend

FastAPI + PostgreSQL + SQLAlchemy

## Quick start

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://... uvicorn app.main:app --reload
```

## Run tests

```bash
python -m pytest tests/ -v
```

## API docs

Available at `http://localhost:8000/docs` when running.
