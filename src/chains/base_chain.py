import time
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.callbacks import CallbackManagerForChainRun
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.config import settings
from src.utils.logger import agent_logger as logger


class BaseChain(ABC):
    prompt_title: str = "Base Chain"
    prompt_template: str = ""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        self.model_name = model_name or settings.llm.model_name
        self.temperature = temperature
        self.llm = self._init_llm()
        self.output_key = "output"
    
    def _init_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base or None,
        )
    
    @property
    def input_keys(self) -> List[str]:
        return ["question"]
    
    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]
    
    def get_name(self) -> str:
        return self.prompt_title
    
    @abstractmethod
    def description(self) -> str:
        pass
    
    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, str]:
        pass
    
    def run(self, question: str, **kwargs) -> str:
        result = self._call({"question": question, **kwargs})
        return result.get(self.output_key, "")
    
    async def arun(self, question: str, **kwargs) -> str:
        return self.run(question, **kwargs)


class ExampleChain(BaseChain):
    prompt_title: str = "示例对话链"
    prompt_template: str = """你是一个智能助手，请根据用户的问题提供清晰的回答。

用户问题：{question}

请回答："""
    
    def description(self) -> str:
        return "一个简单的对话链示例"
    
    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, str]:
        try:
            begin_time = time.time()
            question = inputs.get("question", "")
            logger.info(f"[{self.prompt_title}] 开始执行, 输入: {question[:100]}...")
            
            prompt = PromptTemplate.from_template(self.prompt_template)
            chain = prompt | self.llm | StrOutputParser()
            
            response = chain.invoke({"question": question})
            
            end_time = time.time()
            logger.info(f"[{self.prompt_title}] 完成, 耗时: {end_time - begin_time:.3f}s")
            
            return {self.output_key: response}
            
        except Exception as e:
            logger.error(f"[{self.prompt_title}] 异常: {e}", exc_info=True)
            return {self.output_key: f"Error: {str(e)}"}


class ExtractionChain(BaseChain):
    prompt_title: str = "信息提取链"
    prompt_template: str = """请从以下文本中提取关键信息，以JSON格式返回。

输入文本：
{question}

请提取以下信息：
1. 时间信息
2. 地点信息  
3. 人物信息
4. 事件描述

请以JSON格式返回结果："""
    
    def description(self) -> str:
        return "从文本中提取结构化信息"
    
    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, str]:
        try:
            begin_time = time.time()
            question = inputs.get("question", "")
            logger.info(f"[{self.prompt_title}] 开始执行")
            
            prompt = PromptTemplate.from_template(self.prompt_template)
            chain = prompt | self.llm | StrOutputParser()
            
            response = chain.invoke({"question": question})
            result = self._parse_response(response)
            
            end_time = time.time()
            logger.info(f"[{self.prompt_title}] 完成, 耗时: {end_time - begin_time:.3f}s")
            
            return {self.output_key: json.dumps(result, ensure_ascii=False)}
            
        except Exception as e:
            logger.error(f"[{self.prompt_title}] 异常: {e}", exc_info=True)
            return {self.output_key: json.dumps(self._default_result(), ensure_ascii=False)}
    
    def _parse_response(self, content: str) -> dict:
        try:
            cleaned = content.strip()
            
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:].rsplit('```', 1)[0].strip()
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:].rsplit('```', 1)[0].strip()
            
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                return json.loads(json_match.group())
            
            return self._default_result()
        except Exception as e:
            logger.error(f"[{self.prompt_title}] JSON解析失败: {e}")
            return self._default_result()
    
    def _default_result(self) -> dict:
        return {
            "time": "",
            "location": "",
            "person": "",
            "event": ""
        }


class ChatChain(BaseChain):
    prompt_title: str = "对话链"
    
    def description(self) -> str:
        return "支持多轮对话的链"
    
    @property
    def input_keys(self) -> List[str]:
        return ["question", "history"]
    
    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, str]:
        try:
            begin_time = time.time()
            question = inputs.get("question", "")
            history = inputs.get("history", [])
            
            logger.info(f"[{self.prompt_title}] 开始执行")
            
            system_prompt = "你是一个智能助手，请根据用户的问题提供清晰的回答。"
            
            messages = [("system", system_prompt)]
            
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(("human", msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(("ai", msg.get("content", "")))
            
            messages.append(("human", "{question}"))
            
            prompt = ChatPromptTemplate.from_messages(messages)
            chain = prompt | self.llm | StrOutputParser()
            
            response = chain.invoke({"question": question})
            
            end_time = time.time()
            logger.info(f"[{self.prompt_title}] 完成, 耗时: {end_time - begin_time:.3f}s")
            
            return {self.output_key: response}
            
        except Exception as e:
            logger.error(f"[{self.prompt_title}] 异常: {e}", exc_info=True)
            return {self.output_key: f"Error: {str(e)}"}


class PromptManager:
    _prompts: Dict[str, str] = {}
    
    @classmethod
    def load_prompt(cls, filename: str, title: str) -> Optional[str]:
        import os
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompts_dir = os.path.join(current_dir, 'prompts')
            file_path = os.path.join(prompts_dir, filename)
            
            if not os.path.exists(file_path):
                logger.error(f"Prompt文件不存在: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            sections = cls._parse_sections(content)
            
            if title in sections:
                return sections[title]
            
            logger.error(f"未找到标题: {title}")
            return None
            
        except Exception as e:
            logger.error(f"加载Prompt失败: {e}")
            return None
    
    @classmethod
    def _parse_sections(cls, content: str) -> Dict[str, str]:
        sections = {}
        parts = re.split(r'^(# .+)$', content, flags=re.MULTILINE)
        
        current_title = None
        current_content = ""
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if part.startswith('# '):
                if current_title is not None:
                    sections[current_title] = current_content.strip()
                current_title = part[2:].strip()
                current_content = ""
            else:
                if current_content:
                    current_content += "\n" + part
                else:
                    current_content = part
        
        if current_title is not None:
            sections[current_title] = current_content.strip()
        
        return sections
