from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Optional, Generic, TypeVar
from pydantic import BaseModel, Field, ValidationError
from app.models.schemas import Agent
from app.tools.context import ToolContext
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseTool(ABC, Generic[T]):
    """
    Abstract base class for all Agent_OS tools.
    Provides strict schema validation via Pydantic V2 and standardized execution context.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of what the tool does (used for LLM prompt generation)."""
        pass

    @property
    @abstractmethod
    def args_schema(self) -> Type[T]:
        """Pydantic model defining the expected input arguments."""
        pass

    @property
    def requires_secrets(self) -> list[str]:
        """List of secret keys required from OpenBao (e.g., ['tavily_api_key'])."""
        return []

    async def validate_and_execute(self, input_data: Dict[str, Any], agent: Agent, context: ToolContext) -> Any:
        """
        Validates input data against the args_schema and then executes the tool.
        """
        try:
            validated_args = self.args_schema.model_validate(input_data)
            return await self.execute(validated_args, agent, context)
        except ValidationError as e:
            logger.error(f"Validation failed for tool {self.name}: {e.json()}")
            raise ValueError(f"Invalid arguments for {self.name}: {e.errors()}")
        except Exception as e:
            logger.exception(f"Execution failed for tool {self.name}")
            raise

    @abstractmethod
    async def execute(self, args: T, agent: Agent, context: ToolContext) -> Any:
        """
        Internal execution logic for the tool. 
        Must be implemented by subclasses.
        """
        pass

    def get_json_schema(self) -> Dict[str, Any]:
        """Returns the JSON schema for the tool's arguments."""
        return self.args_schema.model_json_schema()
