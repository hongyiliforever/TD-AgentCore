import asyncio
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logger import agent_logger as logger


class MCPTransportType(Enum):
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


@dataclass
class MCPToolInfo:
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResourceInfo:
    uri: str
    name: str
    description: str = ""


class MCPClient:
    """
    MCP 客户端 - 用于调用其他 Agent 的能力
    
    只用于 Agent 之间的通信，不涉及 Agent 内部实现
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._connected = False
        self._tools: Dict[str, MCPToolInfo] = {}
        self._resources: Dict[str, MCPResourceInfo] = {}
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self) -> bool:
        logger.info(f"[MCP Client] Connecting to agent: {self.agent_name}")
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        logger.info(f"[MCP Client] Disconnecting from agent: {self.agent_name}")
        self._connected = False
    
    def register_tool(self, tool: MCPToolInfo) -> None:
        self._tools[tool.name] = tool
        logger.info(f"[MCP Client] Tool registered: {tool.name}")
    
    def register_resource(self, resource: MCPResourceInfo) -> None:
        self._resources[resource.uri] = resource
        logger.info(f"[MCP Client] Resource registered: {resource.uri}")
    
    def list_tools(self) -> List[str]:
        return list(self._tools.keys())
    
    def get_tool_info(self, name: str) -> Optional[MCPToolInfo]:
        return self._tools.get(name)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        调用目标 Agent 的工具
        
        注意：这里只是接口定义，实际调用由 MCPConnectionManager 处理
        """
        if not self._connected:
            raise RuntimeError(f"Not connected to agent: {self.agent_name}")
        
        if tool_name not in self._tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        arguments = arguments or {}
        logger.info(f"[MCP Client] Calling tool: {self.agent_name}.{tool_name}")
        
        return {"status": "pending", "message": "Tool call should be handled by MCPConnectionManager"}


class MCPConnectionManager:
    """
    MCP 连接管理器 - 管理 Agent 之间的连接和调用
    
    核心职责：
    1. 管理 Agent 之间的连接
    2. 路由工具调用到目标 Agent
    3. 不涉及 Agent 内部实现
    """
    
    _instance = None
    _connections: Dict[str, MCPClient] = {}
    _agent_handlers: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register_agent(cls, agent_name: str, handler: Any) -> None:
        """
        注册 Agent 的处理器
        
        handler 是 Agent 暴露的 MCP Server
        """
        cls._agent_handlers[agent_name] = handler
        logger.info(f"[MCP Manager] Agent registered: {agent_name}")
    
    @classmethod
    def unregister_agent(cls, agent_name: str) -> None:
        if agent_name in cls._agent_handlers:
            del cls._agent_handlers[agent_name]
            logger.info(f"[MCP Manager] Agent unregistered: {agent_name}")
    
    @classmethod
    def get_client(cls, agent_name: str) -> Optional[MCPClient]:
        return cls._connections.get(agent_name)
    
    @classmethod
    async def connect(cls, agent_name: str) -> MCPClient:
        """
        连接到目标 Agent
        
        返回的客户端只能调用该 Agent 暴露的工具
        """
        if agent_name in cls._connections:
            client = cls._connections[agent_name]
            if client.is_connected:
                return client
        
        client = MCPClient(agent_name)
        await client.connect()
        
        if agent_name in cls._agent_handlers:
            handler = cls._agent_handlers[agent_name]
            tools = handler.list_tools()
            for tool in tools:
                client.register_tool(MCPToolInfo(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.input_schema
                ))
        
        cls._connections[agent_name] = client
        return client
    
    @classmethod
    async def disconnect(cls, agent_name: str) -> None:
        if agent_name in cls._connections:
            await cls._connections[agent_name].disconnect()
            del cls._connections[agent_name]
    
    @classmethod
    async def disconnect_all(cls) -> None:
        for agent_name in list(cls._connections.keys()):
            await cls.disconnect(agent_name)
    
    @classmethod
    def list_connections(cls) -> List[str]:
        return list(cls._connections.keys())
    
    @classmethod
    async def call_tool(cls, agent_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        调用目标 Agent 的工具
        
        这是 Agent 间通信的核心方法
        """
        if agent_name not in cls._agent_handlers:
            raise RuntimeError(f"Agent not registered: {agent_name}")
        
        handler = cls._agent_handlers[agent_name]
        arguments = arguments or {}
        
        logger.info(f"[MCP Manager] Routing call: {agent_name}.{tool_name}")
        
        result = await handler.handle_tool_call(tool_name, arguments)
        return result
    
    @classmethod
    def list_available_agents(cls) -> List[str]:
        return list(cls._agent_handlers.keys())
