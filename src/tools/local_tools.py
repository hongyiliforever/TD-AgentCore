from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, tool

from src.utils.logger import agent_logger as logger


class ToolInput(BaseModel):
    input_text: str = Field(description="Input text for the tool")


class CalculatorInput(BaseModel):
    expression: str = Field(description="Mathematical expression to evaluate")


class SearchInput(BaseModel):
    query: str = Field(description="Search query")
    limit: int = Field(default=5, description="Maximum number of results")


@tool
def get_current_time() -> str:
    """Get the current date and time."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    
    Args:
        expression: A mathematical expression like "2 + 3 * 4"
    
    Returns:
        The result of the calculation
    """
    try:
        allowed_chars = set("0123456789+-*/().% ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"
        
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def word_count(text: str) -> str:
    """
    Count words in a text.
    
    Args:
        text: The text to count words in
    
    Returns:
        The word count
    """
    words = text.split()
    return f"Word count: {len(words)}"


@tool
def reverse_string(text: str) -> str:
    """
    Reverse a string.
    
    Args:
        text: The string to reverse
    
    Returns:
        The reversed string
    """
    return text[::-1]


class LocalToolRegistry:
    _tools: Dict[str, BaseTool] = {}
    
    @classmethod
    def register(cls, tool: BaseTool):
        cls._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")
    
    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        return cls._tools.get(name)
    
    @classmethod
    def get_all_tools(cls) -> List[BaseTool]:
        return list(cls._tools.values())
    
    @classmethod
    def list_tools(cls) -> List[str]:
        return list(cls._tools.keys())


LocalToolRegistry.register(get_current_time)
LocalToolRegistry.register(calculate)
LocalToolRegistry.register(word_count)
LocalToolRegistry.register(reverse_string)


def get_default_tools() -> List[BaseTool]:
    return LocalToolRegistry.get_all_tools()


def create_custom_tool(
    name: str,
    description: str,
    func: callable,
    args_schema: Optional[Type[BaseModel]] = None
) -> BaseTool:
    """
    Create a custom tool dynamically.
    
    Example:
    ```python
    def my_function(input_text: str) -> str:
        return input_text.upper()
    
    tool = create_custom_tool(
        name="uppercase",
        description="Convert text to uppercase",
        func=my_function
    )
    ```
    """
    @tool(name=name)
    def custom_tool(input_text: str) -> str:
        return func(input_text)
    
    custom_tool.description = description
    return custom_tool
