# Render Deployment Guide

## Configuration Files

### 1. `render.yaml` (Repository Root)
Infrastructure-as-code configuration for Render. This file:
- Specifies Python 3.11.11 to avoid pydantic-core Rust build issues
- Sets the root directory to `marketpulse/backend`
- Configures environment variables
- Defines build and start commands

### 2. `marketpulse/backend/runtime.txt`
Backup Python version specification: `python-3.11.11`

## Why Python 3.11.11?

Python 3.14 (currently in alpha/beta) causes build failures with `pydantic-core==2.18.2` because:
- Pydantic-core requires Rust compilation for Python 3.14
- Pre-built wheels are not available for Python 3.14
- Python 3.11.11 is stable and has pre-built wheels for all dependencies

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
1. Verify `render.yaml` is at repository root
2. Check Render Dashboard shows "Blueprint" deployment
3. Try redeploying from Render Dashboard
4. Check build logs for Python version detection

### If pydantic-core build fails:
1. Clear Render build cache
2. Redeploy
3. Check `runtime.txt` exists in `marketpulse/backend/`

## Reference
- [Render Python Version Docs](https://render.com/docs/python-version)
- [Render Blueprint Docs](https://render.com/docs/blueprint-spec)
