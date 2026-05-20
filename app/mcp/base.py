from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field

class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = Field(None, exclude=True)

class MCPResource(BaseModel):
    uri: str
    name: str
    mime_type: Optional[str] = None
    description: Optional[str] = None

class MCPServerConfig(BaseModel):
    name: str
    version: str = "1.0.0"
    tools: List[MCPTool] = []
    resources: List[MCPResource] = []

class MCPServer:
    """
    Base class for MCP Server implementation.
    Allows for dynamic tool and resource registration.
    """
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._tool_registry: Dict[str, Callable] = {}
        for tool in config.tools:
            if tool.handler:
                self.register_tool_handler(tool.name, tool.handler)

    def register_tool_handler(self, tool_name: str, handler: Callable):
        self._tool_registry[tool_name] = handler

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in self._tool_registry:
            raise ValueError(f"Tool {name} not found")
        handler = self._tool_registry[name]
        return await handler(**arguments)

    def get_manifest(self) -> Dict[str, Any]:
        return {
            "mcp_version": "1.0.0",
            "server": {
                "name": self.config.name,
                "version": self.config.version,
            },
            "tools": [t.model_dump(exclude={"handler"}) for t in self.config.tools],
            "resources": [r.model_dump() for r in self.config.resources]
        }
