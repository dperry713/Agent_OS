# Agent Runtime OS

A production-grade, multi-tenant deterministic infrastructure platform for agent execution.

## Features

- **Control Plane**: FastAPI REST API for tenant, agent, and task management.
- **Deterministic Kernel**: Asyncio-based task scheduler and lifecycle manager.
- **Secure Runtime**: Policy-enforced tool execution with default-deny behavior.
- **Isolated Memory**: Per-tenant and per-agent isolated key-value storage (SQLite).
- **FOSS Stack**: Built entirely with open-source technologies (FastAPI, Redis, PostgreSQL/SQLite, Docker).

## Architecture

1. **Control Plane**: REST API layer.
2. **Kernel**: Asynchronous task scheduling and dispatching.
3. **Runtime**: Secure execution of tools.
4. **Tools**: Plugin-based tool system (Echo, Time built-in).
5. **Policy**: Default-deny enforcement and audit logging.
6. **Memory**: Boundary-enforced storage.

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development)

### Running with Docker

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   python app/main.py
   ```

### Running Tests

```bash
pytest tests/
```

### Running the Example Script

Ensure the server is running, then:
```bash
python scripts/example.py
```

## Multi-Tenancy Isolation

- No shared memory between tenants.
- Independent security policies per tenant.
- Resource limits (agents, tasks) per tenant.
- Audit logs tagged with tenant IDs.
