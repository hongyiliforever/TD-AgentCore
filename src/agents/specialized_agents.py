from typing import Optional

from src.agents.example_agent import BaseAgent
from src.config import settings
from src.utils.logger import agent_logger as logger


class ResearcherAgent(BaseAgent):
    name: str = "Researcher Agent"
    description: str = "负责信息收集和研究的智能体"
    
    SYSTEM_PROMPT = """你是一个专业的研究员智能体。
你的任务是：
1. 分析用户的问题
2. 收集相关信息
3. 提供结构化的研究结果

请用清晰的格式输出研究结果。"""
    
    def run(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Researching: {input_text[:100]}...")
        
        try:
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = self.llm.invoke(messages)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            logger.info(f"[{self.name}] Research completed")
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"
    
    async def arun(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Researching (async): {input_text[:100]}...")
        
        try:
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = await self.llm.ainvoke(messages)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            logger.info(f"[{self.name}] Research completed (async)")
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"


class WriterAgent(BaseAgent):
    name: str = "Writer Agent"
    description: str = "负责内容撰写和编辑的智能体"
    
    SYSTEM_PROMPT = """你是一个专业的内容撰写智能体。
你的任务是：
1. 根据提供的研究结果撰写内容
2. 确保内容清晰、有逻辑
3. 使用合适的格式和结构

请输出高质量的撰写内容。"""
    
    def run(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Writing based on: {input_text[:100]}...")
        
        try:
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = self.llm.invoke(messages)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            logger.info(f"[{self.name}] Writing completed")
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"
    
    async def arun(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Writing (async): {input_text[:100]}...")
        
        try:
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = await self.llm.ainvoke(messages)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            logger.info(f"[{self.name}] Writing completed (async)")
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"


class ReviewerAgent(BaseAgent):
    name: str = "Reviewer Agent"
    description: str = "负责内容审核和质量检查的智能体"
    
    SYSTEM_PROMPT = """你是一个专业的内容审核智能体。
你的任务是：
1. 审核内容的准确性和完整性
2. 检查逻辑和结构
3. 提供改进建议

请输出审核结果和改进建议。"""
    
    def run(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Reviewing: {input_text[:100]}...")
        
        try:
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = self.llm.invoke(messages)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            logger.info(f"[{self.name}] Review completed")
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"
    
    async def arun(self, input_text: str, **kwargs) -> str:
        logger.info(f"[{self.name}] Reviewing (async): {input_text[:100]}...")
        
        try:
            messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
            response = await self.llm.ainvoke(messages)
            
            self.add_to_history("user", input_text)
            self.add_to_history("assistant", response.content)
            
            logger.info(f"[{self.name}] Review completed (async)")
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return f"Error: {str(e)}"
