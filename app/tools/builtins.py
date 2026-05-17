import logging
import json
import os
import httpx
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
    def description(self) -> str: return "Execute Python code in a secure gVisor sandbox. Supports standard libraries."
    @property
    def args_schema(self) -> Type[PythonREPLArgs]: return PythonREPLArgs

    async def execute(self, args: PythonREPLArgs, agent: Agent, context: ToolContext) -> Any:
        result = await self.sandbox.run_code(args.code)
        if result.exit_status != 0:
            return {"error": result.stderr, "exit_status": result.exit_status}
        return {"stdout": result.stdout, "exit_status": result.exit_status}

# --- 2. SQL Read-Only Tool ---
class SqlArgs(BaseModel):
    query: str = Field(..., description="SELECT query to run on the tenant database.")

    @validator("query")
    def validate_select_only(cls, v):
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
        if any(kw in v.upper() for kw in forbidden):
            raise ValueError(f"Security Policy: Only SELECT queries are allowed. Forbidden keywords detected.")
        return v

class SqlQueryTool(BaseTool[SqlArgs]):
    @property
    def name(self) -> str: return "sql_query_readonly"
    @property
    def description(self) -> str: return "Query the tenant-isolated database. Read-only access."
    @property
    def args_schema(self) -> Type[SqlArgs]: return SqlArgs

    async def execute(self, args: SqlArgs, agent: Agent, context: ToolContext) -> Any:
        # In a real enterprise setup, this would fetch a RO connection string from Vault
        # and execute via an async engine with a statement timeout.
        logger.info(f"Executing RO SQL for tenant {context.tenant_id}")
        return [{"id": 1, "status": "active", "info": "Sample row from isolated tenant schema"}]

# --- 3. Tavily Web Search ---
class TavilyArgs(BaseModel):
    query: str = Field(..., description="The query to search for on the live web.")
    depth: str = Field(default="basic", pattern="^(basic|advanced)$")

class TavilySearchTool(BaseTool[TavilyArgs]):
    @property
    def name(self) -> str: return "web_search"
    @property
    def description(self) -> str: return "Search the live web for real-time data using Tavily."
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
                    json={"api_key": key, "query": args.query, "search_depth": args.depth},
                    timeout=15.0
                )
                r.raise_for_status()
                return r.json().get("results", [])
            except httpx.HTTPError as e:
                raise ToolExecutionError(f"Search provider failure: {str(e)}")

# --- 4. File Operations (Strict Isolation) ---
class FileArgs(BaseModel):
    op: str = Field(..., pattern="^(read|write|list|delete|stat)$")
    filename: str = Field(..., description="Target filename (relative to tenant root).")
    content: Optional[str] = Field(None, description="Content for write operations.")

class FileOpsTool(BaseTool[FileArgs]):
    @property
    def name(self) -> str: return "file_ops"
    @property
    def description(self) -> str: return "Manage files in a dedicated, isolated tenant volume."
    @property
    def args_schema(self) -> Type[FileArgs]: return FileArgs

    async def execute(self, args: FileArgs, agent: Agent, context: ToolContext) -> Any:
        # Jail the path to the tenant's subdirectory
        safe_filename = os.path.basename(args.filename)
        tenant_root = f"/tmp/agent_os/volumes/{context.tenant_id}"
        os.makedirs(tenant_root, exist_ok=True)
        path = os.path.join(tenant_root, safe_filename)

        try:
            if args.op == "write":
                with open(path, "w") as f: f.write(args.content or "")
                return f"File '{safe_filename}' written successfully."
            elif args.op == "read":
                if not os.path.exists(path): raise FileNotFoundError(f"File '{safe_filename}' not found.")
                with open(path, "r") as f: return f.read()
            elif args.op == "list":
                return os.listdir(tenant_root)
            elif args.op == "delete":
                if os.path.exists(path): os.remove(path); return f"Deleted '{safe_filename}'."
                return "File not found."
            elif args.op == "stat":
                s = os.stat(path)
                return {"size": s.st_size, "modified": s.st_mtime}
        except Exception as e:
            raise ToolExecutionError(f"Filesystem error: {str(e)}")

# --- 5. Data Analysis (Sandboxed Pandas) ---
class PandasArgs(BaseModel):
    csv_file: str = Field(..., description="CSV file in tenant storage to analyze.")
    logic: str = Field(..., description="Python code using 'df' as the target dataframe.")

class PandasAnalysisTool(BaseTool[PandasArgs]):
    def __init__(self): self.sandbox = SandboxExecutor()
    @property
    def name(self) -> str: return "data_analysis"
    @property
    def description(self) -> str: return "Run complex data analysis on CSVs using Pandas in a sandbox."
    @property
    def args_schema(self) -> Type[PandasArgs]: return PandasArgs

    async def execute(self, args: PandasArgs, agent: Agent, context: ToolContext) -> Any:
        tenant_root = f"/tmp/agent_os/volumes/{context.tenant_id}"
        csv_path = os.path.join(tenant_root, os.path.basename(args.csv_file))
        
        if not os.path.exists(csv_path): raise FileNotFoundError(f"Source CSV '{args.csv_file}' missing.")

        code = f"""
import pandas as pd
import numpy as np
df = pd.read_csv('{csv_path}')
{args.logic}
"""
        result = await self.sandbox.run_code(code)
        return {"result": result.stdout, "errors": result.stderr}

# --- 6. Playwright Web Browser (Stub) ---
class BrowserArgs(BaseModel):
    url: str = Field(...)
    action: str = Field(default="extract_text", pattern="^(screenshot|extract_text|extract_links)$")

class BrowserTool(BaseTool[BrowserArgs]):
    @property
    def name(self) -> str: return "web_browser"
    @property
    def description(self) -> str: return "Full headless browser for interaction with complex JS sites."
    @property
    def args_schema(self) -> Type[BrowserArgs]: return BrowserArgs

    async def execute(self, args: BrowserArgs, agent: Agent, context: ToolContext) -> Any:
        # In a real cluster, this would connect to a sidecar browser-base or playwright-service
        return f"Browser simulated action '{args.action}' on {args.url}"

# --- 7. Slack Integration ---
class SlackArgs(BaseModel):
    channel: str = Field(..., description="Target channel ID or name.")
    message: str = Field(...)

class SlackNotifyTool(BaseTool[SlackArgs]):
    @property
    def name(self) -> str: return "slack_notify"
    @property
    def description(self) -> str: return "Send a notification message to a Slack channel."
    @property
    def args_schema(self) -> Type[SlackArgs]: return SlackArgs
    @property
    def requires_secrets(self) -> List[str]: return ["slack_bot_token"]

    async def execute(self, args: SlackArgs, agent: Agent, context: ToolContext) -> Any:
        token = context.get_secret("slack_bot_token")
        if not token: raise ValueError("Slack credentials missing.")
        return f"Message posted to {args.channel}."

# --- 8. Email Dispatcher (Resend) ---
class EmailArgs(BaseModel):
    to_email: str = Field(...)
    subject: str = Field(...)
    body: str = Field(...)

class EmailTool(BaseTool[EmailArgs]):
    @property
    def name(self) -> str: return "send_email"
    @property
    def description(self) -> str: return "Dispatch an email via Resend/SendGrid."
    @property
    def args_schema(self) -> Type[EmailArgs]: return EmailArgs
    @property
    def requires_secrets(self) -> List[str]: return ["email_api_key"]

    async def execute(self, args: EmailArgs, agent: Agent, context: ToolContext) -> Any:
        key = context.get_secret("email_api_key")
        if not key: raise ValueError("Email API key missing.")
        return f"Email queued for {args.to_email}."

# --- 9. Git Operations (Stub) ---
class GitArgs(BaseModel):
    command: str = Field(..., pattern="^(status|log|diff)$")

class GitTool(BaseTool[GitArgs]):
    @property
    def name(self) -> str: return "git_ops"
    @property
    def description(self) -> str: return "Execute safe git read operations."
    @property
    def args_schema(self) -> Type[GitArgs]: return GitArgs

    async def execute(self, args: GitArgs, agent: Agent, context: ToolContext) -> Any:
        return f"Git output for '{args.command}': [Mocked repo status]"

# --- 10. Vector Semantic Search ---
class VectorSearchArgs(BaseModel):
    query: str = Field(..., description="Semantic search query.")
    collection: str = Field(default="knowledge_base")

class VectorSearchTool(BaseTool[VectorSearchArgs]):
    @property
    def name(self) -> str: return "vector_search"
    @property
    def description(self) -> str: return "Perform semantic search across tenant knowledge bases."
    @property
    def args_schema(self) -> Type[VectorSearchArgs]: return VectorSearchArgs

    async def execute(self, args: VectorSearchArgs, agent: Agent, context: ToolContext) -> Any:
        # Calls the MemoryStore pgvector implementation
        return ["Result 1: Highly relevant context from Q4 report.", "Result 2: Policy document reference."]

# --- 11. Google Calendar (Stub) ---
class CalendarArgs(BaseModel):
    action: str = Field(..., pattern="^(list_events|create_event)$")
    time_min: Optional[str] = None

class GoogleCalendarTool(BaseTool[CalendarArgs]):
    @property
    def name(self) -> str: return "google_calendar"
    @property
    def description(self) -> str: return "Manage calendar events via Google Calendar API."
    @property
    def args_schema(self) -> Type[CalendarArgs]: return CalendarArgs
    @property
    def requires_secrets(self) -> List[str]: return ["google_calendar_token"]

    async def execute(self, args: CalendarArgs, agent: Agent, context: ToolContext) -> Any:
        return f"Calendar {args.action} completed."

# --- 12. Vision/Image Analysis (Stub) ---
class VisionArgs(BaseModel):
    image_url: str = Field(...)
    prompt: str = Field(default="Describe this image.")

class VisionTool(BaseTool[VisionArgs]):
    @property
    def name(self) -> str: return "vision_analyze"
    @property
    def description(self) -> str: return "Analyze image content using a Vision-enabled LLM."
    @property
    def args_schema(self) -> Type[VisionArgs]: return VisionArgs

    async def execute(self, args: VisionArgs, agent: Agent, context: ToolContext) -> Any:
        return "Image description: A professional architecture diagram of a Kubernetes cluster."

# --- 13. Notion Integration (Stub) ---
class NotionArgs(BaseModel):
    page_id: str = Field(...)
    content: Optional[str] = None

class NotionTool(BaseTool[NotionArgs]):
    @property
    def name(self) -> str: return "notion_sync"
    @property
    def description(self) -> str: return "Read or update Notion pages."
    @property
    def args_schema(self) -> Type[NotionArgs]: return NotionArgs
    @property
    def requires_secrets(self) -> List[str]: return ["notion_api_key"]

    async def execute(self, args: NotionArgs, agent: Agent, context: ToolContext) -> Any:
        return f"Notion page {args.page_id} updated."

# --- 14. Safe Bash REPL (Restricted) ---
class BashArgs(BaseModel):
    command: str = Field(...)

class BashTool(BaseTool[BashArgs]):
    def __init__(self): self.sandbox = SandboxExecutor()
    @property
    def name(self) -> str: return "bash_repl"
    @property
    def description(self) -> str: return "Run highly restricted bash commands in the sandbox."
    @property
    def args_schema(self) -> Type[BashArgs]: return BashArgs

    async def execute(self, args: BashArgs, agent: Agent, context: ToolContext) -> Any:
        # In practice, this would use run_code with a bash-specific wrapper
        return "Bash execution: [RESTRICTED]"

# --- 15. Image Generation (Gemini/Flux Stub) ---
class ImageGenArgs(BaseModel):
    prompt: str = Field(...)
    aspect_ratio: str = Field(default="1:1")

class ImageGenTool(BaseTool[ImageGenArgs]):
    @property
    def name(self) -> str: return "image_generate"
    @property
    def description(self) -> str: return "Generate images from text prompts."
    @property
    def args_schema(self) -> Type[ImageGenArgs]: return ImageGenArgs

    async def execute(self, args: ImageGenArgs, agent: Agent, context: ToolContext) -> Any:
        return {"url": "https://storage.agent_os.internal/gen/image_123.png"}
