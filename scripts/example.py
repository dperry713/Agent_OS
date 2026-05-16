import httpx
import asyncio
import time

BASE_URL = "http://localhost:8000"

async def run_example():
    async with httpx.AsyncClient() as client:
        print("--- 1. Creating Tenant ---")
        tenant_resp = await client.post(f"{BASE_URL}/tenants", json={
            "tenant_id": "demo_tenant",
            "name": "Demo Tenant",
            "blocked_tools": ["time"]  # Block 'time' tool for demo
        })
        print(tenant_resp.json())

        print("\n--- 2. Creating Agent ---")
        agent_resp = await client.post(f"{BASE_URL}/agents", json={
            "agent_id": "demo_agent",
            "tenant_id": "demo_tenant",
            "name": "Demo Agent"
        })
        print(agent_resp.json())

        print("\n--- 3. Submitting Allowed Task (echo) ---")
        echo_resp = await client.post(
            f"{BASE_URL}/tasks/demo_tenant/demo_agent?tool_name=echo",
            json={"message": "Hello from Agent OS!"}
        )
        task_id = echo_resp.json()["task_id"]
        print(f"Task ID: {task_id}")

        # Poll for result
        for _ in range(5):
            await asyncio.sleep(1)
            task_status = await client.get(f"{BASE_URL}/tasks/{task_id}")
            status = task_status.json()["status"]
            print(f"Status: {status}")
            if status in ["completed", "failed"]:
                print(f"Result: {task_status.json()['result']}")
                break

        print("\n--- 4. Submitting Blocked Task (time) ---")
        time_resp = await client.post(
            f"{BASE_URL}/tasks/demo_tenant/demo_agent?tool_name=time",
            json={}
        )
        task_id_blocked = time_resp.json()["task_id"]
        print(f"Task ID: {task_id_blocked}")

        await asyncio.sleep(1)
        task_status_blocked = await client.get(f"{BASE_URL}/tasks/{task_id_blocked}")
        print(f"Status: {task_status_blocked.json()['status']}")
        print(f"Error: {task_status_blocked.json()['error']}")

if __name__ == "__main__":
    print("Ensure the server is running at http://localhost:8000")
    try:
        asyncio.run(run_example())
    except Exception as e:
        print(f"Error: {e}. Is the server running?")
