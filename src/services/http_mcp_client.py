"""
HTTP MCP Client - 支持跨容器通信的 MCP 客户端

特性：
1. HTTP/HTTPS 调用
2. SSE 流式接收
3. 自动重试
4. 连接池管理
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass

import httpx

from src.utils.logger import agent_logger as logger


@dataclass
class MCPToolInfo:
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPResponse:
    status: str
    result: Any
    error: Optional[str]
    trace_id: str
    duration_ms: int


class HTTPMCPClient:
    """
    HTTP MCP Client - 跨容器通信客户端
    
    特性：
    1. HTTP/HTTPS 调用
    2. SSE 流式接收
    3. 自动重试
    4. 连接池
    """
    
    def __init__(
        self,
        agent_name: str,
        base_url: str,
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        self.agent_name = agent_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._tools: Dict[str, MCPToolInfo] = {}
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self) -> bool:
        """连接到 MCP Server 并获取工具列表"""
        try:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True
            )
            
            response = await self._client.get("/tools")
            response.raise_for_status()
            
            tools_data = response.json().get("tools", [])
            for tool in tools_data:
                self._tools[tool["name"]] = MCPToolInfo(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {})
                )
            
            self._connected = True
            logger.info(
                f"[HTTP MCP Client] Connected to {self.agent_name}, "
                f"tools: {list(self._tools.keys())}"
            )
            return True
            
        except Exception as e:
            logger.error(f"[HTTP MCP Client] Connection failed: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info(f"[HTTP MCP Client] Disconnected from {self.agent_name}")
    
    def list_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self._tools.keys())
    
    def get_tool_info(self, name: str) -> Optional[MCPToolInfo]:
        """获取工具信息"""
        return self._tools.get(name)
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any] = None,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> MCPResponse:
        """
        调用工具（带自动重试）
        """
        if not self._connected or not self._client:
            raise RuntimeError(f"Not connected to {self.agent_name}")
        
        if tool_name not in self._tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        trace_id = trace_id or str(uuid.uuid4())
        arguments = arguments or {}
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                response = await self._client.post(
                    "/tools/call",
                    json={
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "trace_id": trace_id,
                        "task_id": task_id
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                
                return MCPResponse(
                    status=data.get("status", "unknown"),
                    result=data.get("result"),
                    error=data.get("error"),
                    trace_id=data.get("trace_id", trace_id),
                    duration_ms=data.get("duration_ms", int((time.time() - start_time) * 1000))
                )
                
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"[HTTP MCP Client] Tool call failed (attempt {attempt + 1}): "
                    f"{e.response.status_code}"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
            except Exception as e:
                last_error = e
                logger.warning(
                    f"[HTTP MCP Client] Tool call failed (attempt {attempt + 1}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError(f"Tool call failed after {self.max_retries} attempts: {last_error}")
    
    async def call_tool_stream(
        self,
        tool_name: str,
        arguments: Dict[str, Any] = None,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式调用工具（SSE）
        """
        if not self._connected or not self._client:
            raise RuntimeError(f"Not connected to {self.agent_name}")
        
        trace_id = trace_id or str(uuid.uuid4())
        arguments = arguments or {}
        
        async with self._client.stream(
            "POST",
            "/tools/call/stream",
            json={
                "tool_name": tool_name,
                "arguments": arguments,
                "trace_id": trace_id,
                "task_id": task_id
            },
            timeout=self.timeout
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        if "chunk" in data:
                            yield data["chunk"]
                        elif "result" in data:
                            yield data["result"]
                        elif "error" in data:
                            raise RuntimeError(data["error"])
                    except json.JSONDecodeError:
                        continue
    
    async def read_resource(self, uri: str) -> Any:
        """读取资源"""
        if not self._connected or not self._client:
            raise RuntimeError(f"Not connected to {self.agent_name}")
        
        response = await self._client.get(f"/{uri}")
        response.raise_for_status()
        
        data = response.json()
        return data.get("result")


class MCPClientPool:
    """
    MCP 客户端连接池
    
    管理多个 Agent 的连接
    """
    
    _instance = None
    _clients: Dict[str, HTTPMCPClient] = {}
    _agent_urls: Dict[str, str] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register_agent(cls, agent_name: str, base_url: str) -> None:
        """注册 Agent URL"""
        cls._agent_urls[agent_name] = base_url
        logger.info(f"[MCP Client Pool] Agent URL registered: {agent_name} -> {base_url}")
    
    @classmethod
    async def get_client(cls, agent_name: str) -> HTTPMCPClient:
        """获取或创建客户端"""
        if agent_name in cls._clients and cls._clients[agent_name].is_connected:
            return cls._clients[agent_name]
        
        if agent_name not in cls._agent_urls:
            raise ValueError(f"Agent not registered: {agent_name}")
        
        client = HTTPMCPClient(
            agent_name=agent_name,
            base_url=cls._agent_urls[agent_name]
        )
        
        await client.connect()
        cls._clients[agent_name] = client
        
        return client
    
    @classmethod
    async def call_tool(
        cls,
        agent_name: str,
        tool_name: str,
        arguments: Dict[str, Any] = None,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> MCPResponse:
        """便捷方法：直接调用工具"""
        client = await cls.get_client(agent_name)
        return await client.call_tool(tool_name, arguments, trace_id, task_id)
    
    @classmethod
    async def disconnect_all(cls) -> None:
        """断开所有连接"""
        for agent_name, client in list(cls._clients.items()):
            await client.disconnect()
        cls._clients.clear()
        logger.info("[MCP Client Pool] All clients disconnected")
    
    @classmethod
    def list_connections(cls) -> List[str]:
        """列出已连接的 Agent"""
        return [
            name for name, client in cls._clients.items()
            if client.is_connected
        ]
    
    @classmethod
    def list_registered_agents(cls) -> List[str]:
        """列出已注册的 Agent"""
        return list(cls._agent_urls.keys())


def init_client_pool() -> None:
    """初始化客户端池（从环境变量读取配置）"""
    import os
    
    default_agents = {
        "researcher": os.getenv("RESEARCHER_URL", "http://researcher-agent:8002"),
        "writer": os.getenv("WRITER_URL", "http://writer-agent:8003"),
        "reviewer": os.getenv("REVIEWER_URL", "http://reviewer-agent:8004"),
        "orchestrator": os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8001"),
    }
    
    for agent_name, url in default_agents.items():
        MCPClientPool.register_agent(agent_name, url)
