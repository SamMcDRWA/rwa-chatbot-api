# Render Deployment Guide

## Quick Fix for Current Error

The current error is due to missing `setuptools` and Python version compatibility issues.

## Files Added/Updated

1. **`runtime.txt`** - Specifies Python 3.11.9 (more stable than 3.13)
2. **`requirements.txt`** - Updated with setuptools and compatible versions
3. **`requirements-render.txt`** - Alternative requirements file with tested versions

## Render Configuration

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
python enhanced_chat_api.py
```

### Environment Variables Needed
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key
- `TABLEAU_SERVER_URL` - Tableau server URL
- `TABLEAU_PAT_NAME` - Tableau personal access token name
- `TABLEAU_PAT_SECRET` - Tableau personal access token secret
- `TABLEAU_SITE_NAME` - Tableau site name

## Troubleshooting

If you still get setuptools errors:
1. Try using `requirements-render.txt` instead
2. Check that Python version is 3.11.9 (not 3.13)
3. Ensure all environment variables are set

## Alternative: Use requirements-render.txt

If the main requirements.txt still fails, you can:
1. Rename `requirements-render.txt` to `requirements.txt`
2. Commit and push the change
3. Redeploy on Render
