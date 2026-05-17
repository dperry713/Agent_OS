# Agent_OS: Enterprise-Grade Agent Runtime OS

Agent_OS is a production-hardened, multi-tenant, and highly isolated execution environment for autonomous AI agents. It provides a secure "OS" layer that handles compute isolation, tenant data sovereignty, and robust tool execution.

## 🚀 Key Features

- **Bulletproof Isolation**: Hard compute isolation via **gVisor** user-space kernels.
- **Multi-Tenant Architecture**: Strict data isolation using **PostgreSQL Row-Level Security (RLS)**.
- **Dynamic Security**: Ephemeral secret injection from **OpenBao (Vault)**; secrets never touch the database.
- **Distributed Execution**: Scalable task processing via **Celery + RabbitMQ**.
- **Robust Tool System**: 20+ production-grade tools with strict Pydantic validation and sandboxing.
- **Advanced Orchestration**: Native support for **ReAct**, **Plan-and-Execute**, and **Supervisor** patterns.
- **Observability**: End-to-end tracing with **OpenTelemetry** and real-time monitoring via **Prometheus**.

## 🏗 Architecture

```text
Control Plane (FastAPI) <---> Message Broker (RabbitMQ) <---> Worker Plane (Celery + gVisor)
      |                                                        |
      +--> State Layer (Postgres RLS + pgvector)               +--> Sandbox (POSIX Limits)
      +--> Secret Layer (OpenBao)                              +--> Tool Registry
      +--> Cache Layer (Valkey)                                +--> Policy Engine
```

## 🛠 Installation

### Prerequisites
- Docker & Docker Compose
- (Optional) Kubernetes with gVisor support

### Local Development
```bash
docker-compose up --build
```

## 📖 API Documentation

### Submit a Task
`POST /tasks/{tenant_id}/{agent_id}`
Request Body:
```json
{
  "tool_name": "python_repl",
  "input_data": {
    "code": "print('Hello from Agent_OS')"
  }
}
```

### Stream Task Events (WebSocket)
`WS /tasks/{task_id}/stream`
Streams real-time `AgentStep` chunks as the reasoning loop progresses.

## 🛡 Security Model

1. **Jailed Compute**: Every worker runs as a non-privileged user in a gVisor microVM.
2. **Resource Quotas**: Strict POSIX limits on CPU, memory, file descriptors, and disk usage.
3. **Data Sovereignty**: Tenant data is logically isolated at the database level; one tenant's agent can never query another tenant's rows.
4. **Egress Lockdown**: Strict `NetworkPolicy` rules prevent unauthorized data exfiltration.

## 📜 Roadmap

- [x] v1.0 Core Architecture (RLS, Celery, gVisor)
- [x] Robust ReAct & Planning Loops
- [x] 15+ Production Tools
- [x] OpenTelemetry & Prometheus Integration
- [ ] Bring-Your-Own-Compute (BYOC) Support
- [ ] Enterprise Web Console (HTMX)
- [ ] OPA-based Policy Language Integration
