# Agent OS Control Plane

Multi-tenant Agent execution environment following production-grade specs.

## Architecture

- **API:** FastAPI
- **DB:** PostgreSQL with Row Level Security (RLS) prep
- **Worker:** Celery for distributed, async task execution
- **Cache/Broker:** Valkey (Redis-compatible)
- **Deployment:** Docker & docker-compose

## Setup & Execution

### 1. Environment Setup

```bash
cp .env.example .env
```

### 2. Running the System (Local Dev)

Start the entire system using Docker Compose:

```bash
docker-compose up -d --build
```

This will spin up:
- FastAPI server (Port 8000)
- Celery worker
- PostgreSQL Database
- Valkey/Redis Message Broker

### 3. Verification & Execution

Check system health:
```bash
curl http://localhost:8000/health
```

Run tests (from the host, ensuring requirements are installed, or inside the container):
```bash
pip install -r requirements.txt
pytest
```