# Render Deployment Guide

## Configuration Files

### 1. `render.yaml` (Repository Root)
Infrastructure-as-code configuration for Render. This file:
- Specifies Python 3.11.11 via `PYTHON_VERSION` env var
- Sets the root directory to `marketpulse/backend`
- Configures environment variables
- Defines build and start commands

### 2. `marketpulse/backend/.python-version` ⭐ PRIMARY
**Most important file** - Render prioritizes this over all other methods.
Contains: `3.11.11`

### 3. `marketpulse/backend/runtime.txt` (Backup)
Fallback Python version specification: `python-3.11.11`

## Why Python 3.11.11?

Python 3.14 (currently in alpha/beta) causes build failures with `pydantic-core==2.18.2` because:
- Pydantic-core requires Rust compilation for Python 3.14
- Pre-built wheels are not available for Python 3.14
- Python 3.11.11 is stable and has pre-built wheels for all dependencies

## Render Python Version Priority

Render uses this order to determine Python version:
1. **`.python-version`** in service root (highest priority) ⭐
2. `runtime.txt` in service root
3. `PYTHON_VERSION` environment variable
4. System default (may be 3.14+)

Since our `rootDir` is `marketpulse/backend`, the `.python-version` file MUST be in `marketpulse/backend/.python-version`.

## Deployment Methods

### Option A: Using render.yaml (Recommended)
1. Push `render.yaml` to the repository root
2. In Render Dashboard, create a new "Blueprint" service
3. Connect to GitHub repository
4. Render will automatically detect and use `render.yaml`

### Option B: Manual Configuration
1. Create new "Web Service" in Render Dashboard
2. Connect to GitHub repository
3. Configure settings:
   - **Root Directory:** `marketpulse/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Add `PYTHON_VERSION=3.11.11`

## Environment Variables Required

Set these in Render Dashboard:

```bash
DATABASE_URL=<your_database_url>
JWT_SECRET=<generate_strong_secret>
DEMO_MODE=true
```

Optional for production:
```bash
MARKET_API_KEY=<alpha_vantage_or_other_api_key>
NEWS_API_KEY=<news_api_key>
LLM_API_KEY=<openai_api_key>
```

## Verification

After deployment, check:
1. Build logs show `Python 3.11.11` (not 3.14)
2. `pydantic-core` installs from wheel (not building from source)
3. Service starts successfully
4. Health check passes: `curl https://your-app.onrender.com/`

## Troubleshooting

### If still using Python 3.14:
1. Verify `.python-version` exists in `marketpulse/backend/` (NOT repository root)
2. Content should be exactly: `3.11.11` (no prefix, no `python-`)
3. Clear Render build cache in Dashboard
4. Redeploy manually
5. Check build logs - should show: `Using Python version 3.11.11 (from .python-version)`

### If pydantic-core build fails:
1. Ensure `.python-version` has correct content and location
2. Clear Render build cache
3. Redeploy
4. If still fails, check Render Dashboard "Environment" tab for conflicting `PYTHON_VERSION` override

## Reference
- [Render Python Version Docs](https://render.com/docs/python-version)
- [Render Blueprint Docs](https://render.com/docs/blueprint-spec)
