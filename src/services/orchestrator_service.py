"""
编排器服务 - 企业级多 Agent 编排

特性：
1. HTTP API 服务
2. SSE 流式输出
3. 任务编排
4. MCP 路由
"""

import asyncio
import os
import uuid
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.services.state_store import get_state_store, TaskStatus
from src.services.task_manager import get_task_manager, TaskManager
from src.services.http_mcp_client import MCPClientPool, init_client_pool
from src.services.tracing import get_tracer, trace_context_middleware
from src.services.llm_gateway import init_llm_gateway, LLMGateway
from src.utils.logger import agent_logger as logger


class PipelineRequest(BaseModel):
    input: str = Field(..., description="用户输入")
    session_id: Optional[str] = Field(None, description="会话ID")
    agents: List[str] = Field(default=["researcher", "writer", "reviewer"], description="执行的Agent列表")
    stream: bool = Field(default=False, description="是否流式输出")


class PipelineResponse(BaseModel):
    task_id: str
    trace_id: str
    status: str
    message: str


class AgentCallRequest(BaseModel):
    agent_name: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None


class AgentCallResponse(BaseModel):
    status: str
    result: Any
    trace_id: str
    duration_ms: int


app: FastAPI
_state_store = None
_task_manager: TaskManager = None
_llm_gateway: LLMGateway = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _state_store, _task_manager, _llm_gateway
    
    logger.info("[Orchestrator] Starting up...")
    
    _state_store = await get_state_store()
    _task_manager = await get_task_manager()
    _llm_gateway = await init_llm_gateway()
    
    init_client_pool()
    
    _task_manager.register_handler("pipeline", handle_pipeline_task)
    
    logger.info("[Orchestrator] Started successfully")
    
    yield
    
    logger.info("[Orchestrator] Shutting down...")
    await MCPClientPool.disconnect_all()
    await _state_store.disconnect()
    logger.info("[Orchestrator] Shutdown complete")


app = FastAPI(
    title="TD-AgentCore Orchestrator",
    description="企业级多 Agent 编排服务",
    version="1.0.0",
    lifespan=lifespan
)

app.middleware("http")(trace_context_middleware)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}


@app.post("/pipeline", response_model=PipelineResponse)
async def create_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks
):
    """
    创建执行流水线
    
    异步执行，返回 task_id
    """
    task_id = await _task_manager.submit_task(
        task_type="pipeline",
        input_data={
            "input": request.input,
            "agents": request.agents,
            "session_id": request.session_id
        },
        session_id=request.session_id,
        total_steps=len(request.agents)
    )
    
    task = await _state_store.get_task(task_id)
    
    return PipelineResponse(
        task_id=task_id,
        trace_id=task.trace_id,
        status="pending",
        message="Pipeline submitted successfully"
    )


@app.get("/pipeline/{task_id}")
async def get_pipeline_status(task_id: str):
    """获取流水线执行状态"""
    result = await _task_manager.get_task_status(task_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return result


@app.post("/pipeline/{task_id}/cancel")
async def cancel_pipeline(task_id: str):
    """取消流水线"""
    success = await _task_manager.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel task")
    
    return {"status": "cancelled", "task_id": task_id}


@app.post("/pipeline/{task_id}/resume")
async def resume_pipeline(task_id: str):
    """恢复暂停的流水线（断点续传）"""
    success = await _task_manager.resume_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume task")
    
    return {"status": "resumed", "task_id": task_id}


@app.post("/agents/call", response_model=AgentCallResponse)
async def call_agent(request: AgentCallRequest):
    """
    直接调用 Agent
    
    通过 MCP 调用指定的 Agent
    """
    trace_id = request.trace_id or str(uuid.uuid4())
    
    try:
        response = await MCPClientPool.call_tool(
            agent_name=request.agent_name,
            tool_name=request.tool_name,
            arguments=request.arguments,
            trace_id=trace_id
        )
        
        return AgentCallResponse(
            status=response.status,
            result=response.result,
            trace_id=response.trace_id,
            duration_ms=response.duration_ms
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def list_agents():
    """列出可用的 Agent"""
    return {
        "agents": MCPClientPool.list_registered_agents(),
        "connected": MCPClientPool.list_connections()
    }


@app.get("/sse/pipeline/{task_id}")
async def stream_pipeline(task_id: str):
    """
    SSE 流式输出
    
    实时推送任务执行进度
    """
    
    async def event_generator():
        while True:
            result = await _task_manager.get_task_status(task_id)
            
            if not result:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break
            
            yield f"data: {json.dumps(result.__dict__)}\n\n"
            
            if result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.get("/stats")
async def get_stats():
    """获取统计信息"""
    task_stats = await _task_manager.get_stats()
    llm_stats = _llm_gateway.get_stats()
    
    return {
        "tasks": task_stats,
        "llm": llm_stats
    }


async def handle_pipeline_task(
    input_data: Dict[str, Any],
    update_progress,
    trace_id: str
) -> Dict[str, Any]:
    """
    处理流水线任务
    
    按顺序调用各个 Agent
    """
    input_text = input_data.get("input", "")
    agents = input_data.get("agents", ["researcher", "writer", "reviewer"])
    session_id = input_data.get("session_id")
    
    context = {"input": input_text}
    results = {}
    
    for i, agent_name in enumerate(agents):
        await update_progress(
            progress=int((i / len(agents)) * 100),
            current_step=f"Executing {agent_name}"
        )
        
        try:
            response = await MCPClientPool.call_tool(
                agent_name=agent_name,
                tool_name="run",
                arguments={"input": context.get("input", "")},
                trace_id=trace_id,
                task_id=trace_id
            )
            
            if response.status == "success":
                results[agent_name] = response.result
                context["input"] = response.result
            else:
                raise Exception(response.error)
                
        except Exception as e:
            logger.error(f"[Pipeline] Agent {agent_name} failed: {e}")
            raise
    
    await update_progress(progress=100, current_step="completed")
    
    return {
        "final_result": context.get("input"),
        "agent_results": results
    }


import json


def run_server():
    import uvicorn
    
    port = int(os.getenv("ORCHESTRATOR_PORT", "8001"))
    
    uvicorn.run(
        "src.services.orchestrator_service:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )


if __name__ == "__main__":
    run_server()
