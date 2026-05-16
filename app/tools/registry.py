from typing import Dict, Optional
from app.tools.base import BaseTool
from app.tools.builtins import EchoTool, TimeTool, MemoryTool

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_builtins()

    def _register_builtins(self):
        self.register(EchoTool())
        self.register(TimeTool())
        self.register(MemoryTool())

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

# Global registry instance
registry = ToolRegistry()
