from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.mcp.registry import mcp_registry
from app.mcp.base import MCPServerConfig, MCPTool
from app.api.dependencies import get_tenant_id

router = APIRouter()

@router.get("/")
async def list_mcp_servers(tenant_id: str = Depends(get_tenant_id)):
    # In a real implementation, we would filter by tenant_id from a DB
    return {"servers": mcp_registry.list_servers()}

@router.post("/")
async def create_mcp_server(config: MCPServerConfig, tenant_id: str = Depends(get_tenant_id)):
    server = mcp_registry.create_server(config)
    return {"status": "created", "name": config.name}

@router.get("/{server_name}/manifest")
async def get_mcp_manifest(server_name: str, tenant_id: str = Depends(get_tenant_id)):
    server = mcp_registry.get_server(server_name)
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server not found")
    return server.get_manifest()

@router.post("/{server_name}/call")
async def call_mcp_tool(server_name: str, tool_call: Dict[str, Any], tenant_id: str = Depends(get_tenant_id)):
    server = mcp_registry.get_server(server_name)
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server not found")
    
    try:
        result = await server.call_tool(tool_call["name"], tool_call.get("arguments", {}))
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
