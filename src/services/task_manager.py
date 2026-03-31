"""
任务管理器 - 异步任务编排与状态管理

特性：
1. 异步任务提交
2. 任务状态追踪
3. 断点续传
4. 超时处理
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.services.state_store import StateStore, TaskStatus, get_state_store
from src.services.tracing import Tracer, get_tracer
from src.utils.logger import agent_logger as logger


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


@dataclass
class TaskResult:
    task_id: str
    trace_id: str
    status: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: int = 0
    duration_ms: int = 0


class TaskManager:
    """
    任务管理器
    
    特性：
    1. 异步任务提交与执行
    2. 任务状态追踪
    3. 断点续传
    4. 超时处理
    5. 重试机制
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        default_timeout: float = 300.0
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout
        
        self._state_store: Optional[StateStore] = None
        self._tracer: Optional[Tracer] = None
        self._task_handlers: Dict[str, Callable] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def initialize(self) -> None:
        """初始化"""
        self._state_store = await get_state_store()
        self._tracer = get_tracer()
        self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        logger.info(f"[TaskManager] Initialized with max_concurrent={self.max_concurrent_tasks}")
    
    def register_handler(self, task_type: str, handler: Callable) -> None:
        """注册任务处理器"""
        self._task_handlers[task_type] = handler
        logger.info(f"[TaskManager] Handler registered: {task_type}")
    
    async def submit_task(
        self,
        task_type: str,
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        priority: int = 5,
        timeout: Optional[float] = None,
        total_steps: int = 0
    ) -> str:
        """
        提交任务
        
        返回 task_id，任务异步执行
        """
        if task_type not in self._task_handlers:
            raise ValueError(f"No handler for task type: {task_type}")
        
        task = await self._state_store.create_task(
            task_type=task_type,
            input_data=input_data,
            session_id=session_id,
            priority=priority,
            total_steps=total_steps
        )
        
        async def run_task():
            async with self._semaphore:
                await self._execute_task(task.id, timeout or self.default_timeout)
        
        self._running_tasks[task.id] = asyncio.create_task(run_task())
        
        logger.info(f"[TaskManager] Task submitted: {task.id}, type={task_type}")
        
        return task.id
    
    async def _execute_task(self, task_id: str, timeout: float) -> None:
        """执行任务"""
        task = await self._state_store.get_task(task_id)
        if not task:
            return
        
        span = self._tracer.start_trace(
            f"task:{task.task_type}",
            trace_id=task.trace_id
        )
        
        start_time = datetime.utcnow()
        
        try:
            await self._state_store.update_task_status(
                task_id, TaskStatus.RUNNING,
                current_step="initializing"
            )
            
            handler = self._task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler for task type: {task.task_type}")
            
            async def update_progress(progress: int, current_step: str = None):
                await self._state_store.update_task_status(
                    task_id, TaskStatus.RUNNING,
                    progress=progress,
                    current_step=current_step
                )
            
            result = await asyncio.wait_for(
                handler(task.input_data, update_progress, task.trace_id),
                timeout=timeout
            )
            
            await self._state_store.update_task_status(
                task_id, TaskStatus.COMPLETED,
                progress=100,
                output_data=result
            )
            
            self._tracer.finish_span(span, "success")
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.info(
                f"[TaskManager] Task completed: {task_id}, "
                f"duration={duration_ms}ms"
            )
            
        except asyncio.TimeoutError:
            await self._state_store.update_task_status(
                task_id, TaskStatus.FAILED,
                error_message=f"Task timeout after {timeout}s"
            )
            self._tracer.finish_span(span, "error", "timeout")
            logger.error(f"[TaskManager] Task timeout: {task_id}")
            
        except Exception as e:
            await self._state_store.update_task_status(
                task_id, TaskStatus.FAILED,
                error_message=str(e)
            )
            self._tracer.finish_span(span, "error", str(e))
            logger.error(f"[TaskManager] Task failed: {task_id}, error={e}")
            
        finally:
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
    
    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """获取任务状态"""
        task = await self._state_store.get_task(task_id)
        if not task:
            return None
        
        duration_ms = 0
        if task.started_at and task.completed_at:
            duration_ms = int((task.completed_at - task.started_at).total_seconds() * 1000)
        
        return TaskResult(
            task_id=task.id,
            trace_id=task.trace_id,
            status=task.status,
            output=task.output_data,
            error=task.error_message,
            progress=task.progress,
            duration_ms=duration_ms
        )
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            
            await self._state_store.update_task_status(
                task_id, TaskStatus.CANCELLED
            )
            
            logger.info(f"[TaskManager] Task cancelled: {task_id}")
            return True
        
        return False
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        task = await self._state_store.get_task(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        
        await self._state_store.update_task_status(task_id, TaskStatus.PAUSED)
        logger.info(f"[TaskManager] Task paused: {task_id}")
        return True
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务（断点续传）"""
        task = await self._state_store.get_task(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        if task.task_type not in self._task_handlers:
            return False
        
        async def run_task():
            async with self._semaphore:
                await self._execute_task(task_id, self.default_timeout)
        
        self._running_tasks[task_id] = asyncio.create_task(run_task())
        
        await self._state_store.update_task_status(task_id, TaskStatus.RUNNING)
        
        logger.info(f"[TaskManager] Task resumed: {task_id}")
        return True
    
    async def retry_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        task = await self._state_store.get_task(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        
        if task.task_type not in self._task_handlers:
            return False
        
        async with self._state_store.db.acquire() as conn:
            await conn.execute(
                "UPDATE tasks SET retry_count = retry_count + 1 WHERE id = $1",
                task_id
            )
        
        async def run_task():
            async with self._semaphore:
                await self._execute_task(task_id, self.default_timeout)
        
        self._running_tasks[task_id] = asyncio.create_task(run_task())
        
        logger.info(f"[TaskManager] Task retry: {task_id}")
        return True
    
    async def list_tasks(
        self,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 20
    ) -> List[TaskResult]:
        """列出任务"""
        conditions = []
        params = []
        param_idx = 1
        
        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1
        
        if session_id:
            conditions.append(f"session_id = ${param_idx}")
            params.append(session_id)
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = f"""
            SELECT * FROM tasks 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx}
        """
        params.append(limit)
        
        async with self._state_store.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        results = []
        for row in rows:
            duration_ms = 0
            if row["started_at"] and row["completed_at"]:
                duration_ms = int((row["completed_at"] - row["started_at"]).total_seconds() * 1000)
            
            results.append(TaskResult(
                task_id=row["id"],
                trace_id=row["trace_id"],
                status=row["status"],
                output=json.loads(row["output_data"]) if row["output_data"] else None,
                error=row["error_message"],
                progress=row["progress"],
                duration_ms=duration_ms
            ))
        
        return results
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        async with self._state_store.db.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'running') as running,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM tasks
            """)
        
        return {
            "total_tasks": stats["total"],
            "pending": stats["pending"],
            "running": stats["running"],
            "completed": stats["completed"],
            "failed": stats["failed"],
            "active_tasks": len(self._running_tasks)
        }


_task_manager: Optional[TaskManager] = None


async def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
        await _task_manager.initialize()
    return _task_manager


import json
