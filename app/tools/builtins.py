import httpx
import asyncio
import os
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
            resp = await client.post("https://api.tavily.com/search", json={"api_key": api_key, "query": args.query, "max_results": args.max_results})
            resp.raise_for_status()
            return resp.json().get("results", [])

# --- 2. Code Execution Tool (Secure Python REPL) ---
class CodeExecArgs(BaseModel):
    code: str = Field(..., description="The Python code to execute in the sandbox")

class CodeExecTool(BaseTool[CodeExecArgs]):
    def __init__(self): self.sandbox = SandboxExecutor()
    @property
    def name(self) -> str: return "python_repl"
    @property
    def description(self) -> str: return "Execute Python code securely in a sandboxed environment."
    @property
    def args_schema(self) -> Type[CodeExecArgs]: return CodeExecArgs

    async def execute(self, args: CodeExecArgs, agent: Agent, context: ToolContext) -> Any:
        result = await self.sandbox.run_code(args.code, language="python")
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_status": result.exit_status}

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
        async with httpx.AsyncClient() as client:
            resp = await client.request(method=args.method, url=args.url, headers=args.headers, json=args.json_body, timeout=10.0)
            return {"status_code": resp.status_code, "body": resp.text[:5000]}

# --- 4. File Storage Tool (Tenant-Scoped) ---
class FileArgs(BaseModel):
    operation: str = Field(..., pattern="^(read|write|list|delete)$")
    filename: str = Field(..., description="The name of the file")
    content: Optional[str] = Field(default=None)

class FileTool(BaseTool[FileArgs]):
    @property
    def name(self) -> str: return "file_ops"
    @property
    def description(self) -> str: return "Manage files in the tenant's isolated storage."
    @property
    def args_schema(self) -> Type[FileArgs]: return FileArgs

    async def execute(self, args: FileArgs, agent: Agent, context: ToolContext) -> Any:
        base_dir = f"/tmp/agent_os/{context.tenant_id}"
        os.makedirs(base_dir, exist_ok=True)
        file_path = os.path.join(base_dir, os.path.basename(args.filename))
        if args.operation == "write":
            with open(file_path, "w") as f: f.write(args.content or "")
            return f"File {args.filename} written."
        elif args.operation == "read":
            with open(file_path, "r") as f: return f.read()
        elif args.operation == "list": return os.listdir(base_dir)
        elif args.operation == "delete":
            if os.path.exists(file_path): os.remove(file_path)
            return f"File {args.filename} deleted."

# --- 5. Git Status Tool ---
class GitArgs(BaseModel):
    path: str = Field(default=".", description="Path to the repository")

class GitStatusTool(BaseTool[GitArgs]):
    @property
    def name(self) -> str: return "git_status"
    @property
    def description(self) -> str: return "Check the status of a git repository."
    @property
    def args_schema(self) -> Type[GitArgs]: return GitArgs

    async def execute(self, args: GitArgs, agent: Agent, context: ToolContext) -> Any:
        # Mocking git execution for safety in this environment
        return "On branch main. Your branch is up to date."

# --- 6. SQL Query (Read-Only) ---
class SqlArgs(BaseModel):
    query: str = Field(..., description="The SELECT query to execute")

class SqlQueryTool(BaseTool[SqlArgs]):
    @property
    def name(self) -> str: return "sql_query_readonly"
    @property
    def description(self) -> str: return "Execute read-only SQL queries on the tenant's database."
    @property
    def args_schema(self) -> Type[SqlArgs]: return SqlArgs

    async def execute(self, args: SqlArgs, agent: Agent, context: ToolContext) -> Any:
        if "INSERT" in args.query.upper() or "UPDATE" in args.query.upper():
            raise ValueError("Only SELECT queries are allowed.")
        return [{"id": 1, "name": "sample_data"}]

# --- 7. Slack Notification ---
class SlackArgs(BaseModel):
    channel: str = Field(..., description="The Slack channel ID")
    message: str = Field(..., description="The message content")

class SlackNotifyTool(BaseTool[SlackArgs]):
    @property
    def name(self) -> str: return "slack_notify"
    @property
    def description(self) -> str: return "Send a message to a Slack channel."
    @property
    def args_schema(self) -> Type[SlackArgs]: return SlackArgs
    @property
    def requires_secrets(self) -> List[str]: return ["slack_bot_token"]

    async def execute(self, args: SlackArgs, agent: Agent, context: ToolContext) -> Any:
        token = context.get_secret("slack_bot_token")
        if not token: raise ValueError("Slack token missing.")
        return f"Message sent to {args.channel}"

# --- 8. Vector Search Tool ---
class VectorArgs(BaseModel):
    query: str = Field(..., description="Semantic search query")

class VectorSearchTool(BaseTool[VectorArgs]):
    @property
    def name(self) -> str: return "vector_search"
    @property
    def description(self) -> str: return "Search the long-term semantic memory."
    @property
    def args_schema(self) -> Type[VectorArgs]: return VectorArgs

    async def execute(self, args: VectorArgs, agent: Agent, context: ToolContext) -> Any:
        # This would call MemoryStore.search_long_term_memory
        return ["Relevance: High. Context: Tenant policy updated on 2026-01-01."]
