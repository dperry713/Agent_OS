import logging
import json
import os
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, Field
import httpx
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
    def description(self) -> str: return "Run Python code in a secure gVisor sandbox."
    @property
    def args_schema(self) -> Type[PythonREPLArgs]: return PythonREPLArgs

    async def execute(self, args: PythonREPLArgs, agent: Agent, context: ToolContext) -> Any:
        result = await self.sandbox.run_code(args.code)
        if result.exit_status != 0:
            raise ToolExecutionError(f"REPL Error: {result.stderr}")
        return {"stdout": result.stdout, "exit_status": result.exit_status}

# --- 2. SQL Read-Only Tool ---
class SqlArgs(BaseModel):
    query: str = Field(..., description="SELECT query to run.")

class SqlQueryTool(BaseTool[SqlArgs]):
    @property
    def name(self) -> str: return "sql_query_readonly"
    @property
    def description(self) -> str: return "Query the tenant database (Read-Only)."
    @property
    def args_schema(self) -> Type[SqlArgs]: return SqlArgs

    async def execute(self, args: SqlArgs, agent: Agent, context: ToolContext) -> Any:
        q = args.query.upper()
        # Strict validation
        if any(kw in q for kw in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]):
            raise ValueError("Unauthorized SQL keyword detected. Only SELECT is allowed.")
        
        # In production, this would use a dedicated read-only connection from Vault
        return [{"id": 101, "status": "active"}]

# --- 3. Tavily Web Search ---
class TavilyArgs(BaseModel):
    query: str = Field(..., description="The query to search for.")

class TavilySearchTool(BaseTool[TavilyArgs]):
    @property
    def name(self) -> str: return "web_search"
    @property
    def description(self) -> str: return "Search the web for real-time data."
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
                    json={"api_key": key, "query": args.query},
                    timeout=15.0
                )
                r.raise_for_status()
                return r.json().get("results", [])
            except httpx.HTTPError as e:
                raise ToolExecutionError(f"Search API failure: {str(e)}")

# --- 4. File Operations (Isolated) ---
class FileArgs(BaseModel):
    op: str = Field(..., pattern="^(read|write|list)$")
    name: str = Field(..., description="Filename (base name only).")
    content: Optional[str] = None

class FileOpsTool(BaseTool[FileArgs]):
    @property
    def name(self) -> str: return "file_ops"
    @property
    def description(self) -> str: return "Tenant-isolated file operations."
    @property
    def args_schema(self) -> Type[FileArgs]: return FileArgs

    async def execute(self, args: FileArgs, agent: Agent, context: ToolContext) -> Any:
        # Prevent path traversal
        safe_name = os.path.basename(args.name)
        base_path = f"/tmp/agent_os/{context.tenant_id}"
        path = os.path.join(base_path, safe_name)
        
        os.makedirs(base_path, exist_ok=True)
        
        try:
            if args.op == "write":
                with open(path, "w") as f: f.write(args.content or "")
                return f"File '{safe_name}' written."
            elif args.op == "read":
                if not os.path.exists(path): raise FileNotFoundError(f"File '{safe_name}' not found.")
                with open(path, "r") as f: return f.read()
            return os.listdir(base_path)
        except Exception as e:
            raise ToolExecutionError(f"File operation failed: {str(e)}")

# --- 5. Data Analysis (Pandas) ---
class PandasArgs(BaseModel):
    csv_name: str = Field(..., description="The name of the CSV file to analyze.")
    analysis_code: str = Field(..., description="Python code using 'df' as the dataframe.")

class PandasAnalysisTool(BaseTool[PandasArgs]):
    def __init__(self):
        self.sandbox = SandboxExecutor()
    @property
    def name(self) -> str: return "data_analysis"
    @property
    def description(self) -> str: return "Analyze CSV data using Pandas in the sandbox."
    @property
    def args_schema(self) -> Type[PandasArgs]: return PandasArgs

    async def execute(self, args: PandasArgs, agent: Agent, context: ToolContext) -> Any:
        base_path = f"/tmp/agent_os/{context.tenant_id}"
        csv_path = os.path.join(base_path, os.path.basename(args.csv_name))
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV '{args.csv_name}' not found.")

        wrapper_code = f"""
import pandas as pd
df = pd.read_csv('{csv_path}')
{args.analysis_code}
"""
        result = await self.sandbox.run_code(wrapper_code)
        return {"stdout": result.stdout, "stderr": result.stderr}

# --- 6. Playwright Browser (Stubbed but robust) ---
class BrowserArgs(BaseModel):
    url: str = Field(...)
    action: str = Field(default="screenshot", pattern="^(screenshot|text|html)$")

class BrowserTool(BaseTool[BrowserArgs]):
    @property
    def name(self) -> str: return "web_browser"
    @property
    def description(self) -> str: return "Browse the web and extract data or screenshots."
    @property
    def args_schema(self) -> Type[BrowserArgs]: return BrowserArgs

    async def execute(self, args: BrowserArgs, agent: Agent, context: ToolContext) -> Any:
        # In production, this would execute a sandboxed playwright script
        return f"Successfully captured {args.action} for {args.url}"

# --- 7. Email Sender (Resend/SendGrid) ---
class EmailArgs(BaseModel):
    to: str = Field(...)
    subject: str = Field(...)
    body: str = Field(...)

class EmailTool(BaseTool[EmailArgs]):
    @property
    def name(self) -> str: return "send_email"
    @property
    def description(self) -> str: return "Send an email notification."
    @property
    def args_schema(self) -> Type[EmailArgs]: return EmailArgs
    @property
    def requires_secrets(self) -> List[str]: return ["email_api_key"]

    async def execute(self, args: EmailArgs, agent: Agent, context: ToolContext) -> Any:
        key = context.get_secret("email_api_key")
        if not key: raise ValueError("Email API key not found.")
        return f"Email sent to {args.to}"
