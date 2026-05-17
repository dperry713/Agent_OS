from typing import Dict, Optional, List, Any
from app.tools.base import BaseTool
from app.tools.builtins import (
    SearchTool, CodeExecTool, HttpTool, FileTool,
    GitStatusTool, SqlQueryTool, SlackNotifyTool, VectorSearchTool
)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_builtins()

    def _register_builtins(self):
        self.register(SearchTool())
        self.register(CodeExecTool())
        self.register(HttpTool())
        self.register(FileTool())
        self.register(GitStatusTool())
        self.register(SqlQueryTool())
        self.register(SlackNotifyTool())
        self.register(VectorSearchTool())

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schemas for all registered tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.get_json_schema()
            }
            for tool in self._tools.values()
        ]

# Global registry instance
registry = ToolRegistry()
