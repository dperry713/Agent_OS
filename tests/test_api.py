import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from app.main import app, system_registry, kernel, memory_store
from app.models.schemas import Tenant, Agent, TaskStatus

@pytest.fixture(autouse=True)
def clear_registry():
    system_registry.tenants = {}
    system_registry.agents = {}
    # Use sync wrapper to reset if needed, but here we just clear data
    kernel.tasks = {}
    # Clear queue (accessing private to be sure)
    if kernel._queue:
        while not kernel._queue.empty():
            try:
                kernel._queue.get_nowait()
            except:
                break

@pytest.fixture(scope="module")
def client():
    # Use TestClient as context manager to trigger lifespan
    with TestClient(app) as c:
        yield c

def test_api_tenant_creation(client):
    response = client.post("/tenants", json={"tenant_id": "api_t1", "name": "API Tenant"})
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "api_t1"

def test_api_agent_creation(client):
    client.post("/tenants", json={"tenant_id": "api_t2", "name": "API Tenant"})
    response = client.post("/agents", json={"agent_id": "api_a1", "tenant_id": "api_t2", "name": "API Agent"})
    assert response.status_code == 200
    assert response.json()["agent_id"] == "api_a1"

def test_api_full_flow(client):
    # Setup
    client.post("/tenants", json={"tenant_id": "flow_t", "name": "Flow Tenant"})
    client.post("/agents", json={"agent_id": "flow_a", "tenant_id": "flow_t", "name": "Flow Agent"})
    
    # Submit Task
    response = client.post("/tasks/flow_t/flow_a?tool_name=echo", json={"message": "hello api"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Poll for completion
    max_retries = 30
    status = "queued"
    for _ in range(max_retries):
        time.sleep(0.2)
        resp = client.get(f"/tasks/{task_id}")
        status = resp.json()["status"]
        if status == "completed":
            break
    
    assert status == "completed"
    assert resp.json()["result"] == {"output": "hello api"}

def test_api_unauthorized_agent(client):
    client.post("/tenants", json={"tenant_id": "t_owner", "name": "Owner"})
    client.post("/tenants", json={"tenant_id": "t_other", "name": "Other"})
    client.post("/agents", json={"agent_id": "a_owner", "tenant_id": "t_owner", "name": "Agent"})
    
    # Try to submit task for t_owner agent using t_other tenant path
    response = client.post("/tasks/t_other/a_owner?tool_name=echo", json={})
    assert response.status_code == 403 # Forbidden
