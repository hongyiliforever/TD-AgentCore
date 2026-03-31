"""
状态存储模块 - PostgreSQL + Redis 双层存储

架构：
- PostgreSQL: 持久化存储（断点续传、长期记忆）
- Redis: 缓存层（高频访问的状态数据）
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import asyncpg
import redis.asyncio as redis
from pydantic import BaseModel

from src.utils.logger import agent_logger as logger


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TaskModel(BaseModel):
    id: str
    trace_id: str
    session_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    task_type: str
    status: str = TaskStatus.PENDING
    priority: int = 5
    input_data: Dict[str, Any] = {}
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: int = 0
    current_step: Optional[str] = None
    total_steps: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AgentStateModel(BaseModel):
    id: str
    task_id: str
    agent_name: str
    status: str = "idle"
    current_action: Optional[str] = None
    context_data: Dict[str, Any] = {}
    execution_log: List[Dict[str, Any]] = []
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None


class StateStore:
    """
    状态存储 - PostgreSQL + Redis 双层架构
    
    PostgreSQL:
    - 任务状态持久化
    - Agent 状态持久化
    - 执行日志
    - 长期记忆（向量存储）
    
    Redis:
    - 高频访问的上下文数据
    - 会话缓存
    - 分布式锁
    """
    
    def __init__(
        self,
        database_url: str,
        redis_url: str = "redis://localhost:6379/0"
    ):
        self.database_url = database_url
        self.redis_url = redis_url
        self._pool: Optional[asyncpg.Pool] = None
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self.database_url, min_size=5, max_size=20)
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        logger.info("[StateStore] Connected to PostgreSQL and Redis")
    
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
        if self._redis:
            await self._redis.close()
        logger.info("[StateStore] Disconnected from PostgreSQL and Redis")
    
    @property
    def db(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("Not connected to database")
        return self._pool
    
    @property
    def cache(self) -> redis.Redis:
        if not self._redis:
            raise RuntimeError("Not connected to redis")
        return self._redis
    
    async def create_task(
        self,
        task_type: str,
        input_data: Dict[str, Any],
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        priority: int = 5,
        total_steps: int = 0
    ) -> TaskModel:
        trace_id = trace_id or str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks 
                (id, trace_id, session_id, parent_task_id, task_type, priority, input_data, total_steps)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                task_id, trace_id, session_id, parent_task_id,
                task_type, priority, json.dumps(input_data), total_steps
            )
        
        task = TaskModel(
            id=row["id"],
            trace_id=row["trace_id"],
            session_id=row["session_id"],
            parent_task_id=row["parent_task_id"],
            task_type=row["task_type"],
            status=row["status"],
            priority=row["priority"],
            input_data=json.loads(row["input_data"]) if isinstance(row["input_data"], str) else row["input_data"],
            output_data=json.loads(row["output_data"]) if row["output_data"] else None,
            error_message=row["error_message"],
            progress=row["progress"],
            current_step=row["current_step"],
            total_steps=row["total_steps"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            expires_at=row["expires_at"]
        )
        
        await self.cache.setex(f"task:{task_id}", 3600, task.model_dump_json())
        
        logger.info(f"[StateStore] Task created: {task_id}")
        return task
    
    async def get_task(self, task_id: str) -> Optional[TaskModel]:
        cached = await self.cache.get(f"task:{task_id}")
        if cached:
            return TaskModel.model_validate_json(cached)
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1", task_id
            )
        
        if not row:
            return None
        
        task = TaskModel(
            id=row["id"],
            trace_id=row["trace_id"],
            session_id=row["session_id"],
            parent_task_id=row["parent_task_id"],
            task_type=row["task_type"],
            status=row["status"],
            priority=row["priority"],
            input_data=json.loads(row["input_data"]) if isinstance(row["input_data"], str) else row["input_data"],
            output_data=json.loads(row["output_data"]) if row["output_data"] else None,
            error_message=row["error_message"],
            progress=row["progress"],
            current_step=row["current_step"],
            total_steps=row["total_steps"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            expires_at=row["expires_at"]
        )
        
        await self.cache.setex(f"task:{task_id}", 3600, task.model_dump_json())
        return task
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        updates = ["status = $2", "updated_at = NOW()"]
        params = [task_id, status]
        param_idx = 3
        
        if status == TaskStatus.RUNNING:
            updates.append(f"started_at = ${param_idx}")
            params.append(datetime.utcnow())
            param_idx += 1
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            updates.append(f"completed_at = ${param_idx}")
            params.append(datetime.utcnow())
            param_idx += 1
        
        if progress is not None:
            updates.append(f"progress = ${param_idx}")
            params.append(progress)
            param_idx += 1
        
        if current_step is not None:
            updates.append(f"current_step = ${param_idx}")
            params.append(current_step)
            param_idx += 1
        
        if output_data is not None:
            updates.append(f"output_data = ${param_idx}")
            params.append(json.dumps(output_data))
            param_idx += 1
        
        if error_message is not None:
            updates.append(f"error_message = ${param_idx}")
            params.append(error_message)
            param_idx += 1
        
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = $1"
        
        async with self.db.acquire() as conn:
            await conn.execute(query, *params)
        
        await self.cache.delete(f"task:{task_id}")
        
        logger.info(f"[StateStore] Task {task_id} status updated to {status}")
    
    async def create_agent_state(
        self,
        task_id: str,
        agent_name: str,
        context_data: Dict[str, Any] = None,
        max_retries: int = 3
    ) -> AgentStateModel:
        state_id = str(uuid.uuid4())
        context_data = context_data or {}
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO agent_states 
                (id, task_id, agent_name, context_data, max_retries)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                state_id, task_id, agent_name, json.dumps(context_data), max_retries
            )
        
        state = AgentStateModel(
            id=row["id"],
            task_id=row["task_id"],
            agent_name=row["agent_name"],
            status=row["status"],
            current_action=row["current_action"],
            context_data=json.loads(row["context_data"]) if isinstance(row["context_data"], str) else row["context_data"],
            execution_log=json.loads(row["execution_log"]) if isinstance(row["execution_log"], str) else row["execution_log"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
        
        await self.cache.setex(f"agent_state:{state_id}", 3600, state.model_dump_json())
        
        logger.info(f"[StateStore] Agent state created: {state_id} for {agent_name}")
        return state
    
    async def get_agent_state(self, state_id: str) -> Optional[AgentStateModel]:
        cached = await self.cache.get(f"agent_state:{state_id}")
        if cached:
            return AgentStateModel.model_validate_json(cached)
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_states WHERE id = $1", state_id
            )
        
        if not row:
            return None
        
        state = AgentStateModel(
            id=row["id"],
            task_id=row["task_id"],
            agent_name=row["agent_name"],
            status=row["status"],
            current_action=row["current_action"],
            context_data=json.loads(row["context_data"]) if isinstance(row["context_data"], str) else row["context_data"],
            execution_log=json.loads(row["execution_log"]) if isinstance(row["execution_log"], str) else row["execution_log"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
        
        await self.cache.setex(f"agent_state:{state_id}", 3600, state.model_dump_json())
        return state
    
    async def update_agent_context(
        self,
        state_id: str,
        context_data: Dict[str, Any],
        merge: bool = True
    ) -> None:
        if merge:
            current = await self.get_agent_state(state_id)
            if current:
                context_data = {**current.context_data, **context_data}
        
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE agent_states 
                SET context_data = $2, updated_at = NOW()
                WHERE id = $1
                """,
                state_id, json.dumps(context_data)
            )
        
        await self.cache.delete(f"agent_state:{state_id}")
        
        logger.info(f"[StateStore] Agent state {state_id} context updated")
    
    async def log_btree_execution(
        self,
        task_id: str,
        agent_state_id: str,
        node_name: str,
        node_type: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        node_path: Optional[str] = None
    ) -> None:
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO btree_execution_logs 
                (task_id, agent_state_id, node_name, node_type, node_path, status, output_data, error_message, duration_ms, completed_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                """,
                task_id, agent_state_id, node_name, node_type, node_path,
                status, json.dumps(output_data) if output_data else None,
                error_message, duration_ms
            )
    
    async def log_mcp_call(
        self,
        trace_id: str,
        source_agent: str,
        target_agent: str,
        tool_name: str,
        request_data: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> str:
        log_id = str(uuid.uuid4())
        
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mcp_call_logs 
                (id, trace_id, task_id, source_agent, target_agent, tool_name, request_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                log_id, trace_id, task_id, source_agent, target_agent, tool_name, json.dumps(request_data)
            )
        
        return log_id
    
    async def complete_mcp_call(
        self,
        log_id: str,
        response_data: Dict[str, Any],
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> None:
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE mcp_call_logs 
                SET response_data = $2, status = $3, error_message = $4, duration_ms = $5, completed_at = NOW()
                WHERE id = $1
                """,
                log_id, json.dumps(response_data), status, error_message, duration_ms
            )
    
    async def store_memory(
        self,
        session_id: str,
        agent_name: str,
        content: str,
        memory_type: str = "conversation",
        metadata: Dict[str, Any] = None,
        embedding: List[float] = None,
        expires_hours: int = 168
    ) -> str:
        memory_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_memories 
                (id, session_id, agent_name, memory_type, content, content_embedding, metadata, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                memory_id, session_id, agent_name, memory_type, content,
                embedding, json.dumps(metadata or {}), expires_at
            )
        
        return memory_id
    
    async def search_memories(
        self,
        session_id: str,
        query_embedding: List[float],
        agent_name: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        async with self.db.acquire() as conn:
            if agent_name:
                rows = await conn.fetch(
                    """
                    SELECT id, content, memory_type, metadata, created_at,
                           1 - (content_embedding <=> $3::vector) as similarity
                    FROM agent_memories
                    WHERE session_id = $1 AND agent_name = $2
                    ORDER BY content_embedding <=> $3::vector
                    LIMIT $4
                    """,
                    session_id, agent_name, query_embedding, limit
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, content, memory_type, agent_name, metadata, created_at,
                           1 - (content_embedding <=> $2::vector) as similarity
                    FROM agent_memories
                    WHERE session_id = $1
                    ORDER BY content_embedding <=> $2::vector
                    LIMIT $3
                    """,
                    session_id, query_embedding, limit
                )
        
        return [
            {
                "id": row["id"],
                "content": row["content"],
                "memory_type": row["memory_type"],
                "agent_name": row.get("agent_name"),
                "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                "similarity": row["similarity"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            for row in rows
        ]
    
    async def acquire_lock(self, resource: str, ttl: int = 30) -> bool:
        lock_key = f"lock:{resource}"
        lock_value = str(uuid.uuid4())
        
        acquired = await self.cache.set(lock_key, lock_value, nx=True, ex=ttl)
        
        if acquired:
            return True
        return False
    
    async def release_lock(self, resource: str) -> None:
        await self.cache.delete(f"lock:{resource}")


_state_store: Optional[StateStore] = None


async def get_state_store() -> StateStore:
    global _state_store
    if _state_store is None:
        import os
        database_url = os.getenv("DATABASE_URL", "postgresql://agentcore:agentcore123@localhost:5432/agentcore")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        _state_store = StateStore(database_url, redis_url)
        await _state_store.connect()
    
    return _state_store
