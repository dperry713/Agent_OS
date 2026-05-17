# Agent Runtime OS (Enterprise Edition)

A production-grade, horizontally scalable, multi-tenant deterministic infrastructure platform for agent execution.

## Enterprise Architecture

- **Control Plane**: Stateless FastAPI REST API. Handles tenant/agent management and task ingestion.
- **Worker Plane**: Distributed Celery workers running on a gVisor runtime for hard compute isolation.
- **Message Broker**: RabbitMQ (Apache 2.0) for durable task queueing.
- **State Layer**: 
    - **PostgreSQL**: Primary persistent storage with **Row-Level Security (RLS)** for strict tenant data isolation.
    - **Valkey**: Distributed cache for session state and rate limiting.
- **Security**: 
    - **OpenBao**: Dynamic secret management (LLM API keys).
    - **gVisor**: Sandbox runtime for agent tool execution.
    - **K8s Network Policies**: Egress lockdown for worker pods.
- **Observability**: OpenTelemetry instrumentation with distributed tracing.
- **Scaling**: KEDA event-driven autoscaling based on RabbitMQ queue length.

## Getting Started

### Prerequisites

- Docker & Docker Compose
- (Optional) Kubernetes cluster (RKE2 recommended) with gVisor and KEDA.

### Running Locally (Docker Compose)

1. Build and start the entire stack:
   ```bash
   docker-compose up --build
   ```

2. Initialize the Database and OpenBao secrets:
   ```bash
   docker-compose exec api python scripts/initialize_enterprise.py
   ```

3. The API is available at `http://localhost:8000`.

### Running Tests

```bash
pytest tests/
```

### Kubernetes Deployment

The production-ready manifests are located in the `k8s/` directory.

1. Create the necessary secrets (`agent-os-secrets`).
2. Apply the manifests:
   ```bash
   kubectl apply -f k8s/
   ```

## Multi-Tenancy Isolation

- **Compute**: Every agent task runs in a gVisor sandbox.
- **Data**: Row-Level Security (RLS) in PostgreSQL ensures a tenant can only see its own rows.
- **Secrets**: Dynamic injection from OpenBao ensures secrets never persist in the primary DB.
- **Network**: Strict egress policies restrict worker communication to allowlisted endpoints.
