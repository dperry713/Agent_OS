from typing import Dict, Optional, List, Any, Type
from app.tools.base import BaseTool
from app.tools.builtins import (
    PythonREPLTool, SqlQueryTool, TavilySearchTool, 
    FileOpsTool, GitStatusTool, VectorSearchTool,
    PandasAnalysisTool, BrowserTool, EmailTool
)
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Enterprise Tool Registry with auto-discovery and versioning."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_builtins()

    def _register_builtins(self):
        self.register(PythonREPLTool())
        self.register(SqlQueryTool())
        self.register(TavilySearchTool())
        self.register(FileOpsTool())
        self.register(GitStatusTool())
        self.register(VectorSearchTool())
        self.register(PandasAnalysisTool())
        self.register(BrowserTool())
        self.register(EmailTool())

    def register(self, tool: BaseTool):
        if tool.name in self._tools:
            logger.warning(f"Overwriting tool: {tool.name}")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

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
                "parameters": tool.get_json_schema(),
                "metadata": {
                    "requires_secrets": tool.requires_secrets
                }
            }
            for tool in self._tools.values()
        ]

# Global registry instance
registry = ToolRegistry()
