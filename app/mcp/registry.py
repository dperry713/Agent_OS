from typing import List, Dict, Any, Optional
from app.mcp.base import MCPServer, MCPServerConfig, MCPTool

class MCPRegistry:
    """
    Central registry for managing multiple MCP server instances.
    """
    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}

    def create_server(self, config: MCPServerConfig) -> MCPServer:
        server = MCPServer(config)
        self._servers[config.name] = server
        return server

    def get_server(self, name: str) -> Optional[MCPServer]:
        return self._servers.get(name)

    def list_servers(self) -> List[str]:
        return list(self._servers.keys())

mcp_registry = MCPRegistry()

# Example: Pre-register a default system MCP server
default_config = MCPServerConfig(
    name="system-mcp",
    tools=[
        MCPTool(
            name="echo",
            description="Echo back the input",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}}
        )
    ]
)

async def echo_handler(message: str):
    return {"message": message}

system_server = mcp_registry.create_server(default_config)
system_server.register_tool_handler("echo", echo_handler)
