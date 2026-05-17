import httpx
import asyncio
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from app.tools.base import BaseTool
from app.models.schemas import Agent
from app.tools.context import ToolContext
from app.runtime.sandbox import SandboxExecutor

# --- 1. Web Search Tool (Tavily) ---

class SearchArgs(BaseModel):
    query: str = Field(..., description="The search query to execute")
    max_results: int = Field(default=5, ge=1, le=10)

class SearchTool(BaseTool[SearchArgs]):
    @property
    def name(self) -> str: return "web_search"
    
    @property
    def description(self) -> str: return "Search the web for real-time information using Tavily API."
    
    @property
    def args_schema(self) -> Type[SearchArgs]: return SearchArgs
    
    @property
    def requires_secrets(self) -> List[str]: return ["tavily_api_key"]

    async def execute(self, args: SearchArgs, agent: Agent, context: ToolContext) -> Any:
        api_key = context.get_secret("tavily_api_key")
        if not api_key: raise ValueError("Tavily API key not found in Vault.")
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": args.query, "max_results": args.max_results}
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

# --- 2. Code Execution Tool (Secure Python REPL) ---

class CodeExecArgs(BaseModel):
    code: str = Field(..., description="The Python code to execute in the sandbox")

class CodeExecTool(BaseTool[CodeExecArgs]):
    def __init__(self):
        self.sandbox = SandboxExecutor()

    @property
    def name(self) -> str: return "python_repl"
    
    @property
    def description(self) -> str: return "Execute Python code securely in a sandboxed environment."
    
    @property
    def args_schema(self) -> Type[CodeExecArgs]: return CodeExecArgs

    async def execute(self, args: CodeExecArgs, agent: Agent, context: ToolContext) -> Any:
        # Note: In a real implementation, we'd use run_code which handles subprocesses
        result = await self.sandbox.run_code(args.code, language="python")
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code
        }

# --- 3. HTTP Client Tool (Safe Requests) ---

class HttpArgs(BaseModel):
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|DELETE)$")
    url: str = Field(..., description="The URL to request")
    headers: Dict[str, str] = Field(default_factory=dict)
    json_body: Optional[Dict[str, Any]] = Field(default=None)

class HttpTool(BaseTool[HttpArgs]):
    @property
    def name(self) -> str: return "http_client"
    
    @property
    def description(self) -> str: return "Make HTTP requests to external APIs."
    
    @property
    def args_schema(self) -> Type[HttpArgs]: return HttpArgs

    async def execute(self, args: HttpArgs, agent: Agent, context: ToolContext) -> Any:
        # Note: In production, egress is controlled by K8s NetworkPolicy
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=args.method,
                url=args.url,
                headers=args.headers,
                json=args.json_body,
                timeout=10.0
            )
            return {
                "status_code": resp.status_code,
                "body": resp.text[:5000] # Limit response size
            }

# --- 4. File Storage Tool (Tenant-Scoped) ---

class FileArgs(BaseModel):
    operation: str = Field(..., pattern="^(read|write|list|delete)$")
    filename: str = Field(..., description="The name of the file")
    content: Optional[str] = Field(default=None, description="Content for write operation")

class FileTool(BaseTool[FileArgs]):
    @property
    def name(self) -> str: return "file_ops"
    
    @property
    def description(self) -> str: return "Manage files in the tenant's isolated storage."
    
    @property
    def args_schema(self) -> Type[FileArgs]: return FileArgs

    async def execute(self, args: FileArgs, agent: Agent, context: ToolContext) -> Any:
        # Tenant isolation: Files are stored in /tmp/<tenant_id>/
        base_dir = f"/tmp/agent_os/{context.tenant_id}"
        os.makedirs(base_dir, exist_ok=True)
        file_path = os.path.join(base_dir, os.path.basename(args.filename))

        if args.operation == "write":
            with open(file_path, "w") as f: f.write(args.content or "")
            return f"File {args.filename} written successfully."
        elif args.operation == "read":
            if not os.path.exists(file_path): raise FileNotFoundError(f"File {args.filename} not found.")
            with open(file_path, "r") as f: return f.read()
        elif args.operation == "list":
            return os.listdir(base_dir)
        elif args.operation == "delete":
            if os.path.exists(file_path): os.remove(file_path)
            return f"File {args.filename} deleted."

import os
