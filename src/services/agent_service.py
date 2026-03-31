"""
Agent 服务 - 单个 Agent 的独立服务

特性：
1. HTTP API 服务
2. MCP 协议支持
3. 行为树执行
4. 状态持久化
"""

import os
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.services.http_mcp_server import HTTPMCPServer, create_agent_server
from src.services.state_store import get_state_store
from src.services.llm_gateway import init_llm_gateway
from src.services.tracing import get_tracer, trace_context_middleware
from src.utils.logger import agent_logger as logger


app: FastAPI
_mcp_server: HTTPMCPServer = None
_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mcp_server, _agent
    
    agent_name = os.getenv("AGENT_NAME", "agent")
    agent_type = os.getenv("AGENT_TYPE", "example")
    
    logger.info(f"[Agent Service] Starting {agent_name} ({agent_type})...")
    
    state_store = await get_state_store()
    llm_gateway = await init_llm_gateway()
    
    _agent = create_agent_instance(agent_type)
    
    _mcp_server = create_agent_server(
        agent_name=agent_name,
        agent_class=type(_agent),
        tool_name="run",
        tool_description=f"Execute {agent_name} agent"
    )
    
    for route in _mcp_server.create_app().routes:
        app.routes.append(route)
    
    logger.info(f"[Agent Service] {agent_name} started successfully")
    
    yield
    
    logger.info(f"[Agent Service] {agent_name} shutting down...")
    await state_store.disconnect()


app = FastAPI(
    title="TD-AgentCore Agent Service",
    description="独立 Agent 服务",
    version="1.0.0",
    lifespan=lifespan
)

app.middleware("http")(trace_context_middleware)


@app.get("/health")
async def health_check():
    agent_name = os.getenv("AGENT_NAME", "agent")
    return {"status": "healthy", "agent": agent_name}


def create_agent_instance(agent_type: str):
    """根据类型创建 Agent 实例"""
    if agent_type == "researcher":
        from src.agents.specialized_agents import ResearcherAgent
        return ResearcherAgent()
    elif agent_type == "writer":
        from src.agents.specialized_agents import WriterAgent
        return WriterAgent()
    elif agent_type == "reviewer":
        from src.agents.specialized_agents import ReviewerAgent
        return ReviewerAgent()
    else:
        from src.agents.example_agent import ExampleAgent
        return ExampleAgent()


def run_server():
    import uvicorn
    
    port = int(os.getenv("PORT", "8002"))
    
    uvicorn.run(
        "src.services.agent_service:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )


if __name__ == "__main__":
    run_server()
