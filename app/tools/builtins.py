from typing import Any, Dict
from datetime import datetime
from app.tools.base import BaseTool
from app.models.schemas import Agent
from app.tools.context import ToolContext

class EchoTool(BaseTool):
    @property
    def name(self) -> str:
        return "echo"

    async def execute(self, input_data: Dict[str, Any], agent: Agent, context: ToolContext) -> Any:
        message = input_data.get("message", "")
        return {"output": message}

class TimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "time"

    async def execute(self, input_data: Dict[str, Any], agent: Agent, context: ToolContext) -> Any:
        return {"current_time": datetime.utcnow().isoformat()}

class MemoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "memory"

    async def execute(self, input_data: Dict[str, Any], agent: Agent, context: ToolContext) -> Any:
        action = input_data.get("action", "get")
        key = input_data.get("key")
        value = input_data.get("value")
        
        if action == "set":
            await context.set_memory(key, value)
            return {"status": "success"}
        elif action == "get":
            val = await context.get_memory(key)
            return {"value": val}
        return {"error": "invalid action"}
