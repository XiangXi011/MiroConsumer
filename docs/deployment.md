# Deployment Guide

## Local Development

1. Clone the repo
2. Install dependencies:
   ```bash
   cd backend
   pip install -e ".[dev]"
   ```
3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env to set LLM_API_KEY, SECRET_KEY, etc.
   ```
4. Start:
   ```bash
   flask run --port 5001
   ```

## Docker Deployment

1. Build image:
   ```bash
   docker compose build
   ```
2. Start:
   ```bash
   docker compose up -d
   ```
3. Access: http://localhost:3000 (frontend), http://localhost:5001 (API)

## Production Deployment Notes

- Must set a strong SECRET_KEY (>= 32 bytes)
- Set CORS_ALLOWED_ORIGINS to actual domain(s)
- Configure LLM_API_KEY and LLM_BASE_URL
- Recommended: configure SENTRY_DSN for error tracking
- Recommended: configure REDIS_URL for RQ queue
- Set RATE_LIMIT_ENABLED=true to enable rate limiting
