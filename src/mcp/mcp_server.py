import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from src.utils.logger import agent_logger as logger


@dataclass
class MCPTool:
    """
    MCP 工具 - Agent 暴露给其他 Agent 调用的能力
    
    注意：这是 Agent 的"对外接口"，不是内部实现
    """
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


@dataclass
class MCPResource:
    """
    MCP 资源 - Agent 暴露给其他 Agent 访问的数据
    """
    uri: str
    name: str
    description: str = ""
    handler: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description
        }


class MCPServer:
    """
    MCP 服务端 - 暴露 Agent 的能力给其他 Agent 调用
    
    核心职责：
    1. 定义 Agent 对外暴露的工具和资源
    2. 处理来自其他 Agent 的调用请求
    3. 不涉及 Agent 内部实现细节
    
    使用示例：
    ```python
    server = MCPServer(name="researcher_agent")
    
    @server.tool(
        name="research",
        description="研究指定主题",
        input_schema={"type": "object", "properties": {"topic": {"type": "string"}}}
    )
    async def research(topic: str) -> str:
        # 调用 Agent 内部逻辑
        agent = ResearcherAgent()
        return await agent.arun(topic)
    ```
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
    
    def tool(self, name: str, description: str = "", input_schema: Dict[str, Any] = None):
        """
        装饰器：注册 MCP 工具
        
        这是 Agent 暴露给其他 Agent 调用的入口
        """
        def decorator(func: Callable) -> Callable:
            tool = MCPTool(
                name=name,
                description=description or func.__doc__ or "",
                input_schema=input_schema or {},
                handler=func
            )
            self._tools[name] = tool
            logger.info(f"[MCP Server] Tool registered: {name} on agent {self.name}")
            return func
        return decorator
    
    def resource(self, uri: str, name: str, description: str = ""):
        """
        装饰器：注册 MCP 资源
        """
        def decorator(func: Callable) -> Callable:
            resource = MCPResource(
                uri=uri,
                name=name,
                description=description,
                handler=func
            )
            self._resources[uri] = resource
            logger.info(f"[MCP Server] Resource registered: {uri} on agent {self.name}")
            return func
        return decorator
    
    def register_tool(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool
        logger.info(f"[MCP Server] Tool registered: {tool.name}")
    
    def register_resource(self, resource: MCPResource) -> None:
        self._resources[resource.uri] = resource
        logger.info(f"[MCP Server] Resource registered: {resource.uri}")
    
    def list_tools(self) -> List[MCPTool]:
        return list(self._tools.values())
    
    def list_resources(self) -> List[MCPResource]:
        return list(self._resources.values())
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        return self._tools.get(name)
    
    def get_resource(self, uri: str) -> Optional[MCPResource]:
        return self._resources.get(uri)
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理来自其他 Agent 的工具调用
        
        这是 MCP 通信的核心入口
        """
        arguments = arguments or {}
        
        if tool_name not in self._tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool = self._tools[tool_name]
        
        if tool.handler is None:
            raise ValueError(f"Tool has no handler: {tool_name}")
        
        logger.info(f"[MCP Server] Handling tool call: {tool_name} on agent {self.name}")
        
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)
            
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"[MCP Server] Tool call error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def handle_resource_read(self, uri: str) -> Dict[str, Any]:
        """
        处理来自其他 Agent 的资源读取
        """
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")
        
        resource = self._resources[uri]
        
        if resource.handler is None:
            raise ValueError(f"Resource has no handler: {uri}")
        
        logger.info(f"[MCP Server] Handling resource read: {uri} on agent {self.name}")
        
        try:
            if asyncio.iscoroutinefunction(resource.handler):
                result = await resource.handler()
            else:
                result = resource.handler()
            
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"[MCP Server] Resource read error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_server_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "tools": [tool.name for tool in self._tools.values()],
            "resources": [resource.uri for resource in self._resources.values()]
        }
