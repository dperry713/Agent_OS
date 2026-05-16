from abc import ABC, abstractmethod
from typing import Any, Dict
from app.models.schemas import Agent
from app.tools.context import ToolContext

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], agent: Agent, context: ToolContext) -> Any:
        pass
