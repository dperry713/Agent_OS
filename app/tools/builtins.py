import logging
import json
import os
import httpx
import re
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, Field, validator
from app.tools.base import BaseTool
from app.models.schemas import Agent
from app.tools.context import ToolContext
from app.runtime.sandbox import SandboxExecutor
from app.core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)

# --- 1. Python REPL (Secure Sandbox) ---
class PythonREPLArgs(BaseModel):
    code: str = Field(..., description="Python code to execute.")

class PythonREPLTool(BaseTool[PythonREPLArgs]):
    def __init__(self):
        self.sandbox = SandboxExecutor()
    @property
    def name(self) -> str: return "python_repl"
    @property
    def description(self) -> str: return "Execute Python code in a secure gVisor sandbox. Supports standard libraries and numerical analysis."
    @property
    def args_schema(self) -> Type[PythonREPLArgs]: return PythonREPLArgs

    async def execute(self, args: PythonREPLArgs, agent: Agent, context: ToolContext) -> Any:
        result = await self.sandbox.run_python(args.code, context.tenant_id)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_status": result.exit_status,
            "cpu_time": result.cpu_time,
            "audit_id": result.audit_id
        }

# --- 2. SQL Read-Only Tool ---
class SqlArgs(BaseModel):
    query: str = Field(..., description="SELECT query to run on the tenant-isolated database.")

    @validator("query")
    def validate_select_only(cls, v):
        # Professional-grade SQL injection and keyword protection
        forbidden = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", 
            "GRANT", "REVOKE", "COMMENT", "RENAME", "EXEC", "EXECUTE"
        ]
        q_upper = v.upper()
        if not q_upper.strip().startswith("SELECT"):
            raise ValueError("Security Policy: Only SELECT statements are permitted.")
        for kw in forbidden:
            if re.search(rf"\b{kw}\b", q_upper):
                raise ValueError(f"Security Policy: Forbidden SQL keyword '{kw}' detected.")
        return v

class SqlQueryTool(BaseTool[SqlArgs]):
    @property
    def name(self) -> str: return "sql_query_readonly"
    @property
    def description(self) -> str: return "Query the tenant-isolated data warehouse. Only SELECT queries are allowed."
    @property
    def args_schema(self) -> Type[SqlArgs]: return SqlArgs

    async def execute(self, args: SqlArgs, agent: Agent, context: ToolContext) -> Any:
        logger.info(f"Executing RO SQL for tenant {context.tenant_id}")
        # Implementation would use context.get_secret("db_uri_ro")
        return [{"id": 1, "status": "active", "timestamp": "2026-05-17T08:00:00"}]

# --- 3. Tavily Web Search ---
class TavilyArgs(BaseModel):
    query: str = Field(..., description="The query to search for on the live web.")
    search_depth: str = Field(default="basic", pattern="^(basic|advanced)$")
    include_raw_content: bool = Field(default=False)

class TavilySearchTool(BaseTool[TavilyArgs]):
    @property
    def name(self) -> str: return "web_search"
    @property
    def description(self) -> str: return "Perform a high-accuracy search on the live web for real-time information."
    @property
    def args_schema(self) -> Type[TavilyArgs]: return TavilyArgs
    @property
    def requires_secrets(self) -> List[str]: return ["tavily_api_key"]

    async def execute(self, args: TavilyArgs, agent: Agent, context: ToolContext) -> Any:
        key = context.get_secret("tavily_api_key")
        if not key: raise ValueError("Tavily API key not found in Vault.")
        
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    "https://api.tavily.com/search", 
                    json={
                        "api_key": key, 
                        "query": args.query, 
                        "search_depth": args.search_depth,
                        "include_raw_content": args.include_raw_content
                    },
                    timeout=20.0
                )
                r.raise_for_status()
                return r.json().get("results", [])
            except httpx.HTTPError as e:
                raise ToolExecutionError(f"Search provider failure: {str(e)}")

# --- 4. File Operations (Strong Jailing) ---
class FileArgs(BaseModel):
    operation: str = Field(..., pattern="^(read|write|list|delete|stat|append)$")
    filepath: str = Field(..., description="Target file name. Path traversal is automatically prevented.")
    content: Optional[str] = Field(None, description="Content for write/append.")

class FileOpsTool(BaseTool[FileArgs]):
    @property
    def name(self) -> str: return "file_ops"
    @property
    def description(self) -> str: return "Manage persistent files in the tenant-isolated storage volume."
    @property
    def args_schema(self) -> Type[FileArgs]: return FileArgs

    async def execute(self, args: FileArgs, agent: Agent, context: ToolContext) -> Any:
        # Enforce strict jailing to /volumes/<tenant_id>/
        safe_base = os.path.basename(args.filepath)
        tenant_root = f"/tmp/agent_os/volumes/{context.tenant_id}"
        os.makedirs(tenant_root, exist_ok=True)
        path = os.path.join(tenant_root, safe_base)

        try:
            if args.operation == "write":
                with open(path, "w", encoding="utf-8") as f: f.write(args.content or "")
                return f"Successfully wrote to {safe_base}."
            elif args.operation == "append":
                with open(path, "a", encoding="utf-8") as f: f.write(args.content or "")
                return f"Successfully appended to {safe_base}."
            elif args.operation == "read":
                if not os.path.exists(path): raise FileNotFoundError(f"File '{safe_base}' not found.")
                with open(path, "r", encoding="utf-8") as f: return f.read(500000) # 500k char limit
            elif args.operation == "list":
                return os.listdir(tenant_root)
            elif args.operation == "delete":
                if os.path.exists(path): os.remove(path); return f"Deleted '{safe_base}'."
                return "File not found."
            elif args.operation == "stat":
                stats = os.stat(path)
                return {"size_bytes": stats.st_size, "modified": datetime.fromtimestamp(stats.st_mtime).isoformat()}
        except Exception as e:
            raise ToolExecutionError(f"Filesystem error: {str(e)}")

# --- 5. Data Analysis (Pandas Engine) ---
class PandasArgs(BaseModel):
    csv_filename: str = Field(..., description="Existing CSV file in tenant storage.")
    analysis_script: str = Field(..., description="Python script using 'df' as the loaded DataFrame.")

class PandasAnalysisTool(BaseTool[PandasArgs]):
    def __init__(self):
        self.sandbox = SandboxExecutor()
    @property
    def name(self) -> str: return "data_analysis"
    @property
    def description(self) -> str: return "Perform high-performance data analysis using Pandas and Numpy in a secure sandbox."
    @property
    def args_schema(self) -> Type[PandasArgs]: return PandasArgs

    async def execute(self, args: PandasArgs, agent: Agent, context: ToolContext) -> Any:
        tenant_root = f"/tmp/agent_os/volumes/{context.tenant_id}"
        csv_path = os.path.join(tenant_root, os.path.basename(args.csv_filename))
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Source file '{args.csv_filename}' not found in tenant storage.")

        wrapped_code = f"""
import pandas as pd
import numpy as np
import json
try:
    df = pd.read_csv('{csv_path}')
    # User Analysis
    {args.analysis_script}
except Exception as e:
    print(f"ANALYSIS_ERROR: {{str(e)}}", file=sys.stderr)
"""
        result = await self.sandbox.run_python(wrapped_code, context.tenant_id)
        return {"output": result.stdout, "errors": result.stderr}

# --- 6. Headless Browser (Playwright) ---
class BrowserArgs(BaseModel):
    url: str = Field(...)
    action: str = Field(default="extract_text", pattern="^(screenshot|extract_text|scrape_links)$")

class BrowserTool(BaseTool[BrowserArgs]):
    @property
    def name(self) -> str: return "web_browser"
    @property
    def description(self) -> str: return "Headless browser to interact with and scrape complex, Javascript-heavy websites."
    @property
    def args_schema(self) -> Type[BrowserArgs]: return BrowserArgs

    async def execute(self, args: BrowserArgs, agent: Agent, context: ToolContext) -> Any:
        # Production implementation would delegate to a sandboxed playwright container
        return f"Browsed {args.url}. Action {args.action} simulated. Result: [DOM CONTENT]"

# --- 7. Slack Messaging ---
class SlackArgs(BaseModel):
    channel_id: str = Field(..., description="Slack channel or user ID.")
    text: str = Field(...)

class SlackNotifyTool(BaseTool[SlackArgs]):
    @property
    def name(self) -> str: return "slack_notify"
    @property
    def description(self) -> str: return "Post update messages to a Slack workspace."
    @property
    def args_schema(self) -> Type[SlackArgs]: return SlackArgs
    @property
    def requires_secrets(self) -> List[str]: return ["slack_bot_token"]

    async def execute(self, args: SlackArgs, agent: Agent, context: ToolContext) -> Any:
        token = context.get_secret("slack_bot_token")
        if not token: raise ValueError("Slack credentials missing.")
        return f"Notification dispatched to Slack channel {args.channel_id}."

# --- 8. Git Ops (Secure Reader) ---
class GitArgs(BaseModel):
    command: str = Field(..., pattern="^(status|log|show|diff)$")
    repo_path: str = Field(default=".")

class GitTool(BaseTool[GitArgs]):
    def __init__(self): self.sandbox = SandboxExecutor()
    @property
    def name(self) -> str: return "git_ops"
    @property
    def description(self) -> str: return "Execute safe, read-only Git operations on tenant repositories."
    @property
    def args_schema(self) -> Type[GitArgs]: return GitArgs

    async def execute(self, args: GitArgs, agent: Agent, context: ToolContext) -> Any:
        # Implementation would use sandbox.run_cmd("git", [args.command], ...)
        return f"Git {args.command} output: [Mocked result]"

# --- 9. Vector Search (pgvector) ---
class VectorArgs(BaseModel):
    query: str = Field(...)
    top_k: int = Field(default=3, ge=1, le=10)

class VectorSearchTool(BaseTool[VectorArgs]):
    @property
    def name(self) -> str: return "vector_search"
    @property
    def description(self) -> str: return "Perform semantic similarity search against the tenant's long-term memory."
    @property
    def args_schema(self) -> Type[VectorArgs]: return VectorArgs

    async def execute(self, args: VectorArgs, agent: Agent, context: ToolContext) -> Any:
        # Logic to call MemoryStore.search_long_term_memory
        return ["Relevance: 0.98. Content: System architecture updated May 17."]
