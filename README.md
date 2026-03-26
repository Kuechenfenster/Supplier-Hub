# Supplier Hub

Dockerized web application for supplier registration with PostgreSQL database.

## Architecture

- **Frontend**: HTML/CSS/JavaScript
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL 15
- **Container**: Docker & Docker Compose

## Quick Start

### Run with Docker Compose

```bash
cd /a0/usr/projects/cosmetic
docker-compose up -d --build
```

### Access

- **Web App**: http://localhost:8080
- **PostgreSQL**: localhost:5432

### Environment Variables

| Variable | Value |
|----------|-------|
| POSTGRES_USER | supplier |
| POSTGRES_PASSWORD | supplier123 |
| POSTGRES_DB | supplier_hub |

## Files

- `docker-compose.yml` - Container orchestration
- `Dockerfile` - Webapp container
- `backend/main.py` - FastAPI application
- `backend/requirements.txt` - Python dependencies
- `index.html` - Frontend
- `assets/logo.png` - HTI Logo

## Stop Application

```bash
docker-compose down
```

## Remove All Data

```bash
docker-compose down -v
```
