# Agent_OS: Enterprise-Grade AI Agent Runtime

Agent_OS is a production-hardened, multi-tenant, and highly isolated execution environment for autonomous AI agents. It provides a secure "OS" layer that handles compute isolation, tenant data sovereignty, and robust tool execution at scale.

## 🚀 Key Features

- **Bulletproof Isolation**: 
  - **gVisor (runsc)**: Hardware-like compute isolation for untrusted tool execution.
  - **Hardened Sandboxing**: Strict POSIX `ulimits`, process group jailing, and immutable root filesystems.
- **Multi-Tenant Architecture**: 
  - **Hardened PostgreSQL RLS**: Tenant isolation enforced via `SECURITY DEFINER` functions and transaction-local variables.
  - **Data Sovereignty**: Logical isolation at the database kernel level; zero cross-tenant visibility.
- **Dynamic Security**: 
  - **Vault AppRole**: Secure machine-to-machine authentication with short-lived tokens and automatic revocation.
  - **Egress Lockdown**: Kubernetes `NetworkPolicies` with strict allowlisting and RFC1918 blocking.
- **Distributed Reliability**: 
  - **Idempotent State Machine**: Optimistic locking via SQLAlchemy versioning ensures consistency across distributed workers.
  - **Advanced Celery**: Dead-letter queues (DLQ), task priority support, and resilient retry policies.
- **Observability (100% Visibility)**: 
  - **Distributed Tracing**: End-to-end OTel tracing with Jaeger.
  - **Structured Logging**: JSON logs via `structlog` with correlation IDs (trace/span/tenant/task).
  - **Tenant Metrics**: Prometheus metrics sharded by `tenant_id` for granular monitoring and billing.
- **Enterprise-Scale Features**:
  - **OPA Integration**: Fine-grained tool access control via Open Policy Agent sidecars.
  - **Autoscaling**: KEDA-driven scaling based on queue depth (scales to zero) + API HPA.
  - **Semantic Caching**: High-performance vector-based result caching to reduce LLM costs and latency.

## 🏗 Architecture

```text
Control Plane (FastAPI) <---> Message Broker (RabbitMQ) <---> Worker Plane (Celery + gVisor)
      |                                                        |
      +--> State Layer (Postgres RLS + HNSW Vector)            +--> Sandbox (ulimits + runsc)
      +--> Secret Layer (Vault AppRole)                        +--> OPA Policy Sidecar
      +--> Cache Layer (Valkey + Semantic Cache)               +--> Audit Log (Signed HMAC)
```

## 🛠 Installation & Deployment

### Local Development (Hardened)
```bash
# Requires VAULT_ROLE_ID and VAULT_SECRET_ID in .env
docker-compose up --build
```

### Production Kubernetes
Deployment is managed via a comprehensive Helm chart supporting:
- **KEDA ScaledObjects** for worker auto-scaling.
- **NetworkPolicies** for network-level isolation.
- **SecurityContexts** (runAsNonRoot, readOnlyRootFilesystem).

## 🛡 Security Model

1. **Jailed Compute**: Every worker runs as a non-privileged user (UID 10001) in a gVisor microVM.
2. **Resource Quotas**: Distributed sliding-window rate limiting via Valkey prevents noisy-neighbor issues.
3. **Tamper-Proof Auditing**: HMAC-SHA256 chained audit logs ensure that execution records cannot be altered or deleted.
4. **Zero-Trust Networking**: Default-deny ingress and explicitly allowlisted egress to verified LLM endpoints only.

## 📜 Roadmap Compliance

- [x] v1.0 Core Architecture (RLS, Celery, gVisor)
- [x] Hardened RLS with SECURITY DEFINER
- [x] Vault AppRole Integration
- [x] Advanced Observability (OTel + Structlog)
- [x] KEDA & HPA Autoscaling
- [x] OPA Policy Integration
- [x] Semantic Vector Caching
- [x] Tamper-Proof Audit Logging
