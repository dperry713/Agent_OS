# Agent_OS Production Infrastructure

## Core Services
- **API:** FastAPI (Python 3.11)
- **DB:** PostgreSQL 16
- **Worker:** Celery
- **Cache/Broker:** Valkey 8.0

## Setup Instructions (Ubuntu/Debian)

### 1. Install gVisor (runsc)
gVisor is required for sandboxed tool execution.

```bash
sudo apt-get update && sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg

curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://gvisor.dev/archive stable main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null

sudo apt-get update && sudo apt-get install -y runsc
```

### 2. Configure Docker for gVisor
Register `runsc` as a Docker runtime.

```bash
sudo runsc install
sudo systemctl restart docker
```

### 3. Verify gVisor
```bash
docker run --rm --runtime=runsc hello-world
```

## Local Development (Non-Linux)
If you are on macOS or Windows, gVisor is not natively supported. 
- Use the **Local-First Architecture** (SQLite/Eager Celery) for testing logic.
- **NEVER** remove `runtime: runsc` from the `docker-compose.yml` in a PR; this is enforced by CI to ensure production safety.

## Secret Management
Production secrets should be managed via OpenBao/Vault.
- Local development uses `.env` (ignored by git).
- Generate production secrets: `vault write -f auth/approle/...`
