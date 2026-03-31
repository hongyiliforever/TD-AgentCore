"""
全链路追踪模块

特性：
1. Trace ID 生成与传递
2. 跨服务追踪
3. 性能指标收集
4. 日志关联
"""

import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from contextvars import ContextVar
import json

from src.utils.logger import agent_logger as logger


_trace_context: ContextVar[Dict[str, Any]] = ContextVar("trace_context", default={})


@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[int] = None
    status: str = "running"
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self, status: str = "success", error: Optional[str] = None):
        self.end_time = time.time()
        self.duration_ms = int((self.end_time - self.start_time) * 1000)
        self.status = status
        if error:
            self.tags["error"] = error
    
    def add_tag(self, key: str, value: Any) -> None:
        self.tags[key] = value
    
    def add_log(self, message: str, **kwargs) -> None:
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            **kwargs
        })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs
        }


class Tracer:
    """
    全链路追踪器
    
    特性：
    1. Trace ID 生成与传递
    2. Span 管理
    3. 性能指标
    4. 日志关联
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._spans: Dict[str, Span] = {}
        self._active_spans: List[str] = []
    
    def start_trace(
        self,
        operation_name: str,
        trace_id: Optional[str] = None,
        tags: Dict[str, Any] = None
    ) -> Span:
        """开始一个新的追踪"""
        trace_id = trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=None,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags or {}
        )
        
        span.add_tag("service", self.service_name)
        
        self._spans[span_id] = span
        self._active_spans.append(span_id)
        
        _trace_context.set({
            "trace_id": trace_id,
            "span_id": span_id
        })
        
        logger.info(f"[Tracer] Trace started: trace_id={trace_id}, operation={operation_name}")
        
        return span
    
    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None,
        tags: Dict[str, Any] = None
    ) -> Span:
        """开始一个新的 Span"""
        ctx = _trace_context.get()
        trace_id = ctx.get("trace_id") or str(uuid.uuid4())
        parent_span_id = parent_span.span_id if parent_span else ctx.get("span_id")
        
        span_id = str(uuid.uuid4())
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags or {}
        )
        
        span.add_tag("service", self.service_name)
        
        self._spans[span_id] = span
        self._active_spans.append(span_id)
        
        _trace_context.set({
            "trace_id": trace_id,
            "span_id": span_id
        })
        
        return span
    
    def finish_span(self, span: Span, status: str = "success", error: Optional[str] = None) -> None:
        """结束 Span"""
        span.finish(status, error)
        
        if span.span_id in self._active_spans:
            self._active_spans.remove(span.span_id)
        
        logger.info(
            f"[Tracer] Span finished: {span.operation_name}, "
            f"duration={span.duration_ms}ms, status={status}"
        )
    
    def get_trace_context(self) -> Dict[str, str]:
        """获取当前追踪上下文（用于传递给下游服务）"""
        ctx = _trace_context.get()
        return {
            "trace_id": ctx.get("trace_id", ""),
            "span_id": ctx.get("span_id", "")
        }
    
    def set_trace_context(self, trace_id: str, span_id: str) -> None:
        """设置追踪上下文（从上游服务接收）"""
        _trace_context.set({
            "trace_id": trace_id,
            "span_id": span_id
        })
    
    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """获取指定追踪的所有 Span"""
        return [
            span.to_dict()
            for span in self._spans.values()
            if span.trace_id == trace_id
        ]
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """获取指定的 Span"""
        return self._spans.get(span_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_spans = len(self._spans)
        completed_spans = sum(1 for s in self._spans.values() if s.end_time)
        avg_duration = (
            sum(s.duration_ms for s in self._spans.values() if s.duration_ms) / completed_spans
            if completed_spans > 0 else 0
        )
        
        return {
            "service_name": self.service_name,
            "total_spans": total_spans,
            "active_spans": len(self._active_spans),
            "completed_spans": completed_spans,
            "avg_duration_ms": avg_duration
        }


_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    global _tracer
    if _tracer is None:
        _tracer = Tracer("td-agentcore")
    return _tracer


def trace_context_middleware(request, call_next):
    """FastAPI 中间件：处理追踪上下文"""
    tracer = get_tracer()
    
    trace_id = request.headers.get("X-Trace-Id")
    span_id = request.headers.get("X-Span-Id")
    
    if trace_id and span_id:
        tracer.set_trace_context(trace_id, span_id)
    
    span = tracer.start_span(f"{request.method} {request.url.path}")
    
    response = call_next(request)
    
    tracer.finish_span(span, status="success" if response.status_code < 400 else "error")
    
    response.headers["X-Trace-Id"] = span.trace_id
    response.headers["X-Span-Id"] = span.span_id
    
    return response


def traced(operation_name: str):
    """装饰器：自动追踪函数调用"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span = tracer.start_span(operation_name)
            
            try:
                result = await func(*args, **kwargs)
                tracer.finish_span(span, "success")
                return result
            except Exception as e:
                tracer.finish_span(span, "error", str(e))
                raise
        
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span = tracer.start_span(operation_name)
            
            try:
                result = func(*args, **kwargs)
                tracer.finish_span(span, "success")
                return result
            except Exception as e:
                tracer.finish_span(span, "error", str(e))
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
