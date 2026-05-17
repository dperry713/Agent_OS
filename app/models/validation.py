from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List

class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    input_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v.isalnum() and "_" not in v:
            raise ValueError("tool_name must be alphanumeric or underscore")
        return v

class LLMResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[ToolCallRequest] = Field(default_factory=list)
