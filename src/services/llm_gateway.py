"""
LLM Gateway - 统一模型调度网关

功能：
1. 多模型统一管理
2. 智能路由（简单任务 -> 小模型，复杂任务 -> 大模型）
3. 自动降级与重试
4. 成本追踪
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from src.utils.logger import agent_logger as logger


class ModelProvider(Enum):
    OPENAI = "openai"
    ALIBABA = "alibaba"
    ZHIPU = "zhipu"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class TaskComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class ModelConfig:
    name: str
    provider: ModelProvider
    api_key: str
    api_base: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_prompt: float = 0.0
    cost_per_1k_completion: float = 0.0
    rate_limit_rpm: int = 60
    priority: int = 5
    is_fallback: bool = False


@dataclass
class LLMResponse:
    content: str
    model_name: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    trace_id: str


class LLMGateway:
    """
    LLM 网关 - 统一模型调度
    
    功能：
    1. 模型路由：根据任务复杂度选择合适的模型
    2. 自动降级：主模型失败时切换到备用模型
    3. 重试机制：网络错误自动重试
    4. 成本追踪：记录每次调用的成本
    5. 速率限制：防止超出 API 限制
    """
    
    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._llms: Dict[str, ChatOpenAI] = {}
        self._call_history: List[Dict[str, Any]] = []
        self._rate_limiters: Dict[str, asyncio.Semaphore] = {}
    
    def register_model(
        self,
        name: str,
        provider: ModelProvider,
        api_key: str,
        api_base: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        cost_per_1k_prompt: float = 0.0,
        cost_per_1k_completion: float = 0.0,
        rate_limit_rpm: int = 60,
        priority: int = 5,
        is_fallback: bool = False
    ) -> None:
        config = ModelConfig(
            name=name,
            provider=provider,
            api_key=api_key,
            api_base=api_base,
            max_tokens=max_tokens,
            temperature=temperature,
            cost_per_1k_prompt=cost_per_1k_prompt,
            cost_per_1k_completion=cost_per_1k_completion,
            rate_limit_rpm=rate_limit_rpm,
            priority=priority,
            is_fallback=is_fallback
        )
        
        self._models[name] = config
        
        self._llms[name] = ChatOpenAI(
            model=name,
            api_key=api_key,
            base_url=api_base,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        self._rate_limiters[name] = asyncio.Semaphore(rate_limit_rpm // 60)
        
        logger.info(f"[LLM Gateway] Model registered: {name} (provider={provider.value}, priority={priority})")
    
    def get_model_for_complexity(self, complexity: TaskComplexity) -> str:
        """
        根据任务复杂度选择模型
        
        简单任务 -> 小模型（便宜、快）
        复杂任务 -> 大模型（质量高）
        """
        if complexity == TaskComplexity.SIMPLE:
            preferred = ["gpt-4o-mini", "gpt-3.5-turbo", "qwen-turbo"]
        elif complexity == TaskComplexity.MEDIUM:
            preferred = ["gpt-4o-mini", "gpt-4o", "glm-4"]
        else:
            preferred = ["gpt-4o", "gpt-4o-mini"]
        
        for model_name in preferred:
            if model_name in self._models:
                return model_name
        
        sorted_models = sorted(
            self._models.values(),
            key=lambda m: m.priority
        )
        return sorted_models[0].name if sorted_models else list(self._models.keys())[0]
    
    def get_fallback_models(self, primary_model: str) -> List[str]:
        """获取备用模型列表"""
        fallbacks = []
        primary_priority = self._models.get(primary_model, ModelConfig(
            name=primary_model, provider=ModelProvider.OPENAI, api_key=""
        )).priority
        
        for name, config in sorted(self._models.items(), key=lambda x: x[1].priority):
            if name != primary_model and config.priority >= primary_priority:
                fallbacks.append(name)
        
        return fallbacks
    
    async def invoke(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None,
        max_retries: int = 3
    ) -> LLMResponse:
        """
        调用 LLM（带自动降级和重试）
        """
        trace_id = trace_id or str(uuid.uuid4())
        
        if model_name is None:
            model_name = self.get_model_for_complexity(complexity)
        
        models_to_try = [model_name] + self.get_fallback_models(model_name)
        
        last_error = None
        
        for current_model in models_to_try:
            for attempt in range(max_retries):
                try:
                    return await self._invoke_single(
                        current_model, messages, trace_id, task_id
                    )
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"[LLM Gateway] Model {current_model} attempt {attempt + 1} failed: {e}"
                    )
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            
            logger.error(f"[LLM Gateway] Model {current_model} exhausted, trying fallback")
        
        raise RuntimeError(f"All models failed. Last error: {last_error}")
    
    async def _invoke_single(
        self,
        model_name: str,
        messages: List[BaseMessage],
        trace_id: str,
        task_id: Optional[str]
    ) -> LLMResponse:
        config = self._models.get(model_name)
        llm = self._llms.get(model_name)
        
        if not config or not llm:
            raise ValueError(f"Model not found: {model_name}")
        
        async with self._rate_limiters[model_name]:
            start_time = time.time()
            
            response = await llm.ainvoke(messages)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            prompt_tokens = response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
            completion_tokens = response.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens
            
            cost_usd = (
                (prompt_tokens / 1000) * config.cost_per_1k_prompt +
                (completion_tokens / 1000) * config.cost_per_1k_completion
            )
            
            llm_response = LLMResponse(
                content=response.content,
                model_name=model_name,
                provider=config.provider.value,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                trace_id=trace_id
            )
            
            await self._log_call(llm_response, task_id)
            
            logger.info(
                f"[LLM Gateway] Call completed: model={model_name}, "
                f"tokens={total_tokens}, latency={latency_ms}ms, cost=${cost_usd:.6f}"
            )
            
            return llm_response
    
    async def _log_call(self, response: LLMResponse, task_id: Optional[str]) -> None:
        call_log = {
            "id": str(uuid.uuid4()),
            "trace_id": response.trace_id,
            "task_id": task_id,
            "model_name": response.model_name,
            "model_provider": response.provider,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "latency_ms": response.latency_ms,
            "cost_usd": response.cost_usd,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._call_history.append(call_log)
        
        if len(self._call_history) > 1000:
            self._call_history = self._call_history[-500:]
    
    async def stream(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        trace_id: Optional[str] = None
    ):
        """
        流式输出
        """
        trace_id = trace_id or str(uuid.uuid4())
        
        if model_name is None:
            model_name = self.get_model_for_complexity(complexity)
        
        llm = self._llms.get(model_name)
        if not llm:
            raise ValueError(f"Model not found: {model_name}")
        
        logger.info(f"[LLM Gateway] Streaming from {model_name}")
        
        async for chunk in llm.astream(messages):
            yield chunk.content
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调用统计"""
        total_calls = len(self._call_history)
        total_tokens = sum(log["total_tokens"] for log in self._call_history)
        total_cost = sum(log["cost_usd"] for log in self._call_history)
        avg_latency = (
            sum(log["latency_ms"] for log in self._call_history) / total_calls
            if total_calls > 0 else 0
        )
        
        model_stats = {}
        for log in self._call_history:
            model = log["model_name"]
            if model not in model_stats:
                model_stats[model] = {"calls": 0, "tokens": 0, "cost": 0}
            model_stats[model]["calls"] += 1
            model_stats[model]["tokens"] += log["total_tokens"]
            model_stats[model]["cost"] += log["cost_usd"]
        
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "avg_latency_ms": avg_latency,
            "models": model_stats
        }


_gateway: Optional[LLMGateway] = None


def get_llm_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway


async def init_llm_gateway() -> LLMGateway:
    import os
    
    gateway = get_llm_gateway()
    
    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_base = os.getenv("OPENAI_API_BASE")
    
    if openai_key:
        gateway.register_model(
            name="gpt-4o-mini",
            provider=ModelProvider.OPENAI,
            api_key=openai_key,
            api_base=openai_base,
            max_tokens=16384,
            temperature=0.7,
            cost_per_1k_prompt=0.15,
            cost_per_1k_completion=0.60,
            rate_limit_rpm=500,
            priority=1
        )
        
        gateway.register_model(
            name="gpt-4o",
            provider=ModelProvider.OPENAI,
            api_key=openai_key,
            api_base=openai_base,
            max_tokens=8192,
            temperature=0.7,
            cost_per_1k_prompt=2.50,
            cost_per_1k_completion=10.00,
            rate_limit_rpm=500,
            priority=2
        )
        
        gateway.register_model(
            name="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            api_key=openai_key,
            api_base=openai_base,
            max_tokens=4096,
            temperature=0.7,
            cost_per_1k_prompt=0.50,
            cost_per_1k_completion=1.50,
            rate_limit_rpm=500,
            priority=3,
            is_fallback=True
        )
    
    return gateway
