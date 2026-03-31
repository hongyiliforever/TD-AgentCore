"""
HTTP MCP Server - 支持跨容器通信的 MCP 服务端

特性：
1. FastAPI 服务
2. SSE 流式输出
3. Pydantic 强类型校验
4. OpenAPI 文档
"""

import asyncio
import json
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.utils.logger import agent_logger as logger


class MCPToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    trace_id: Optional[str] = Field(None, description="追踪ID")
    task_id: Optional[str] = Field(None, description="任务ID")


class MCPToolCallResponse(BaseModel):
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    trace_id: str
    duration_ms: int


class MCPToolSchema(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPServerInfo(BaseModel):
    name: str
    version: str
    tools: List[MCPToolSchema]


class HTTPMCPServer:
    """
    HTTP MCP Server - 支持跨容器通信
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._app: Optional[FastAPI] = None
    
    def tool(
        self,
        name: str,
        description: str = "",
        input_schema: Dict[str, Any] = None
    ):
        """装饰器：注册 MCP 工具"""
        def decorator(func: Callable) -> Callable:
            self._tools[name] = {
                "name": name,
                "description": description or func.__doc__ or "",
                "input_schema": input_schema or {},
                "handler": func
            }
            logger.info(f"[HTTP MCP Server] Tool registered: {name}")
            return func
        return decorator
    
    def resource(
        self,
        uri: str,
        name: str,
        description: str = ""
    ):
        """装饰器：注册 MCP 资源"""
        def decorator(func: Callable) -> Callable:
            self._resources[uri] = {
                "uri": uri,
                "name": name,
                "description": description,
                "handler": func
            }
            logger.info(f"[HTTP MCP Server] Resource registered: {uri}")
            return func
        return decorator
    
    def create_app(self) -> FastAPI:
        """创建 FastAPI 应用"""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info(f"[HTTP MCP Server] {self.name} starting...")
            yield
            logger.info(f"[HTTP MCP Server] {self.name} stopping...")
        
        self._app = FastAPI(
            title=f"MCP Server: {self.name}",
            description=f"MCP Server for {self.name}",
            version=self.version,
            lifespan=lifespan
        )
        
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
        
        return self._app
    
    def _setup_routes(self):
        """设置路由"""
        
        @self._app.get("/health")
        async def health_check():
            return {"status": "healthy", "server": self.name}
        
        @self._app.get("/info", response_model=MCPServerInfo)
        async def get_server_info():
            return MCPServerInfo(
                name=self.name,
                version=self.version,
                tools=[
                    MCPToolSchema(
                        name=t["name"],
                        description=t["description"],
                        input_schema=t["input_schema"]
                    )
                    for t in self._tools.values()
                ]
            )
        
        @self._app.get("/tools")
        async def list_tools():
            return {
                "tools": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t["input_schema"]
                    }
                    for t in self._tools.values()
                ]
            }
        
        @self._app.post("/tools/call", response_model=MCPToolCallResponse)
        async def call_tool(request: MCPToolCallRequest):
            trace_id = request.trace_id or str(uuid.uuid4())
            start_time = time.time()
            
            if request.tool_name not in self._tools:
                raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_name}")
            
            tool = self._tools[request.tool_name]
            handler = tool["handler"]
            
            logger.info(f"[HTTP MCP Server] Tool called: {request.tool_name}, trace_id={trace_id}")
            
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**request.arguments)
                else:
                    result = handler(**request.arguments)
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                return MCPToolCallResponse(
                    status="success",
                    result=result,
                    trace_id=trace_id,
                    duration_ms=duration_ms
                )
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"[HTTP MCP Server] Tool call error: {e}")
                
                return MCPToolCallResponse(
                    status="error",
                    error=str(e),
                    trace_id=trace_id,
                    duration_ms=duration_ms
                )
        
        @self._app.post("/tools/call/stream")
        async def call_tool_stream(request: MCPToolCallRequest):
            """流式调用工具（SSE）"""
            trace_id = request.trace_id or str(uuid.uuid4())
            
            if request.tool_name not in self._tools:
                raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_name}")
            
            tool = self._tools[request.tool_name]
            handler = tool["handler"]
            
            async def event_generator():
                try:
                    if asyncio.iscoroutinefunction(handler):
                        async_gen = handler(**request.arguments)
                        async for chunk in async_gen:
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    else:
                        result = handler(**request.arguments)
                        yield f"data: {json.dumps({'result': result})}\n\n"
                    
                    yield f"data: {json.dumps({'status': 'completed'})}\n\n"
                    
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "X-Trace-Id": trace_id,
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        
        @self._app.get("/resources")
        async def list_resources():
            return {
                "resources": [
                    {
                        "uri": r["uri"],
                        "name": r["name"],
                        "description": r["description"]
                    }
                    for r in self._resources.values()
                ]
            }
        
        @self._app.get("/resources/{uri:path}")
        async def read_resource(uri: str):
            full_uri = f"resources/{uri}"
            
            if full_uri not in self._resources:
                raise HTTPException(status_code=404, detail=f"Resource not found: {full_uri}")
            
            resource = self._resources[full_uri]
            handler = resource["handler"]
            
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler()
                else:
                    result = handler()
                
                return {"status": "success", "result": result}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """运行服务"""
        app = self.create_app()
        uvicorn.run(app, host=host, port=port)


def create_agent_server(
    agent_name: str,
    agent_class: type,
    tool_name: str = "run",
    tool_description: str = ""
) -> HTTPMCPServer:
    """快速创建 Agent 的 MCP Server"""
    server = HTTPMCPServer(name=f"{agent_name}_agent")
    
    @server.tool(
        name=tool_name,
        description=tool_description or f"Execute {agent_name} agent",
        input_schema={
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input for the agent"},
                "context": {"type": "object", "description": "Additional context"}
            },
            "required": ["input"]
        }
    )
    async def run_agent(input: str, context: Dict[str, Any] = None, **kwargs):
        agent = agent_class()
        
        if asyncio.iscoroutinefunction(getattr(agent, 'arun', None)):
            result = await agent.arun(input)
        else:
            result = agent.run(input)
        
        return result
    
    @server.resource(
        uri="info://agent",
        name=f"{agent_name} Agent Info",
        description=f"Information about {agent_name} agent"
    )
    def get_agent_info():
        return {
            "name": agent_name,
            "type": agent_class.__name__,
            "description": agent_class.__doc__ or ""
        }
    
    return server
