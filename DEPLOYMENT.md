# Deployment Guide

## Environment Variables Required

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_USER` | Database username | `ai_trading` |
| `POSTGRES_PASSWORD` | Database password | `<strong-random-password>` |
| `POSTGRES_DB` | Database name | `ai_trading` |
| `DATABASE_URL` | Full async connection string | `postgresql+asyncpg://user:pass@db:5432/ai_trading` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | `<random-256-bit-hex>` |
| `ANTHROPIC_API_KEY` | Claude API key for AI coach | `sk-ant-...` |
| `CORS_ORIGINS` | Allowed frontend origins | `https://yourdomain.com` |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | `https://api.yourdomain.com` |

## Prerequisites

- Docker & Docker Compose v2+
- Domain with SSL certificate (for production)
- Anthropic API key (optional — offline mode works without it)

## Deployment Steps

### 1. Clone and Configure

```bash
git clone <repo-url>
cd AI_Trading
cp .env.example .env
# Edit .env with production values
```

### 2. Generate a Secure Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Run Database Migrations

```bash
# Start just the database first
docker-compose -f docker-compose.prod.yml up -d db

# Run Alembic migrations
docker-compose -f docker-compose.prod.yml run --rm backend \
  alembic upgrade head
```

### 4. Start All Services

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### 5. Verify

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs

# Frontend
open http://localhost:3000
```

## Deployment Checklist

- [ ] Set strong `POSTGRES_PASSWORD` (not the default)
- [ ] Set strong `SECRET_KEY` (min 32 random chars)
- [ ] Set `CORS_ORIGINS` to your actual frontend domain
- [ ] Set `ANTHROPIC_API_KEY` if using AI coach
- [ ] Run database migrations before first start
- [ ] Set up SSL/TLS termination (nginx, Caddy, or cloud LB)
- [ ] Enable database backups
- [ ] Set up log aggregation
- [ ] Configure monitoring alerts for `/health` endpoint

## Troubleshooting

### Database Connection Issues
- Ensure the `db` service is healthy: `docker-compose ps`
- Check logs: `docker-compose logs db`
- Verify `DATABASE_URL` uses the container name `db`, not `localhost`

### Frontend Can't Reach Backend
- Ensure `NEXT_PUBLIC_API_URL` is the externally-accessible backend URL
- Check CORS: `CORS_ORIGINS` must include the frontend's origin

### Missing TimescaleDB Extension
- The `timescale/timescaledb` image includes the extension
- Run `CREATE EXTENSION IF NOT EXISTS timescaledb;` if needed
