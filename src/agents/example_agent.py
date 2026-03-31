from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from src.config import settings
from src.utils.logger import agent_logger as logger


class BaseAgent(ABC):
    name: str = "Base Agent"
    description: str = "Base agent class"
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        self.model_name = model_name or settings.llm.model_name
        self.temperature = temperature
        self.llm = self._init_llm()
        self.history: List[Dict[str, str]] = []
    
    def _init_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base or None,
        )
    
    def _build_messages(self, input_text: str, system_prompt: Optional[str] = None) -> List:
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        for msg in self.history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=input_text))
        return messages
    
    def add_to_history(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
    
    def clear_history(self):
        self.history = []
    
    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        pass
    
    async def arun(self, input_text: str, **kwargs) -> str:
        return self.run(input_text, **kwargs)


class ExampleAgent(BaseAgent):
    name: str = "Example Agent"
    description: str = "A simple example agent demonstrating the framework structure"
    
    SYSTEM_PROMPT = """你是一个智能助手，可以帮助用户解答问题。
请根据用户的问题，提供清晰、准确的回答。
"""
    
    def run(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Processing input: {input_text[:100]}...")
        
        try:
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = self.llm.invoke(messages)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            logger.info(f"[{self.name}] Response generated successfully")
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"
    
    async def arun(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Processing input (async): {input_text[:100]}...")
        
        try:
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = await self.llm.ainvoke(messages)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            logger.info(f"[{self.name}] Response generated successfully (async)")
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"


class ToolAgent(BaseAgent):
    name: str = "Tool Agent"
    description: str = "An agent that can use tools"
    
    SYSTEM_PROMPT = """你是一个可以使用工具的智能助手。
当需要使用工具时，请明确说明要使用的工具和参数。
"""
    
    def __init__(self, tools: Optional[List] = None, **kwargs):
        super().__init__(**kwargs)
        self.tools = tools or []
    
    def run(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Processing with tools: {input_text[:100]}...")
        
        if not self.tools:
            return super().run(input_text, **kwargs)
        
        try:
            llm_with_tools = self.llm.bind_tools(self.tools)
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = llm_with_tools.invoke(messages)
            
            if response.tool_calls:
                logger.info(f"[{self.name}] Tool calls detected: {response.tool_calls}")
                return self._handle_tool_calls(response.tool_calls, input_text)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"
    
    def _handle_tool_calls(self, tool_calls: List, original_input: str) -> str:
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            results.append(f"Tool: {tool_name}, Args: {tool_args}")
        
        return f"Tool calls detected:\n" + "\n".join(results)
