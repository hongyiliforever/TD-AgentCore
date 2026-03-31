import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.agents.example_agent import BaseAgent
from src.mcp.mcp_client import MCPConnectionManager
from src.mcp.mcp_server import MCPServer
from src.utils.logger import agent_logger as logger


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class AgentNode:
    """
    Agent 节点 - 代表一个可被 MCP 调用的 Agent
    
    包含：
    - Agent 实例（内部实现）
    - MCP Server（对外接口）
    - 依赖关系
    """
    name: str
    agent: Optional[BaseAgent] = None
    mcp_server: Optional[MCPServer] = None
    status: AgentStatus = AgentStatus.IDLE
    dependencies: List[str] = field(default_factory=list)
    description: str = ""


class AgentOrchestrator:
    """
    Agent 编排器 - 管理多个 Agent 之间的 MCP 通信
    
    核心职责：
    1. 注册和管理 Agent
    2. 设置 Agent 之间的依赖关系
    3. 编排 Agent 的执行顺序
    4. 通过 MCP 连接 Agent
    
    不涉及：
    - Agent 内部实现
    - 行为树控制
    - 本地工具调用
    """
    
    def __init__(self, name: str = "AgentOrchestrator"):
        self.name = name
        self._agents: Dict[str, AgentNode] = {}
        self._execution_order: List[str] = []
    
    def register_agent(
        self,
        name: str,
        agent: Optional[BaseAgent] = None,
        mcp_server: Optional[MCPServer] = None,
        description: str = "",
        dependencies: List[str] = None
    ) -> AgentNode:
        """
        注册 Agent
        
        如果提供了 mcp_server，会自动注册到 MCPConnectionManager
        """
        if mcp_server is None:
            mcp_server = MCPServer(name=name)
        
        node = AgentNode(
            name=name,
            agent=agent,
            mcp_server=mcp_server,
            description=description,
            dependencies=dependencies or []
        )
        
        self._agents[name] = node
        
        MCPConnectionManager.register_agent(name, mcp_server)
        
        logger.info(f"[Orchestrator] Agent registered: {name}")
        return node
    
    def get_agent(self, name: str) -> Optional[AgentNode]:
        return self._agents.get(name)
    
    def list_agents(self) -> List[str]:
        return list(self._agents.keys())
    
    def set_execution_order(self, order: List[str]) -> None:
        """
        设置执行顺序
        
        执行顺序决定了 Agent 之间的数据流向
        """
        for agent_name in order:
            if agent_name not in self._agents:
                raise ValueError(f"Agent not found: {agent_name}")
        self._execution_order = order
        logger.info(f"[Orchestrator] Execution order set: {order}")
    
    def _topological_sort(self) -> List[str]:
        """
        根据依赖关系进行拓扑排序
        """
        visited = set()
        result = []
        temp_visited = set()
        
        def visit(name: str):
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected: {name}")
            if name in visited:
                return
            
            temp_visited.add(name)
            agent = self._agents.get(name)
            if agent:
                for dep in agent.dependencies:
                    if dep in self._agents:
                        visit(dep)
            
            temp_visited.remove(name)
            visited.add(name)
            result.append(name)
        
        for name in self._agents:
            visit(name)
        
        return result
    
    async def call_agent(self, agent_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        通过 MCP 调用指定 Agent 的工具
        
        这是 Agent 间通信的核心方法
        """
        node = self._agents.get(agent_name)
        if not node:
            raise ValueError(f"Agent not found: {agent_name}")
        
        node.status = AgentStatus.RUNNING
        logger.info(f"[Orchestrator] Calling agent: {agent_name}.{tool_name}")
        
        try:
            result = await MCPConnectionManager.call_tool(agent_name, tool_name, arguments)
            node.status = AgentStatus.IDLE
            return result
            
        except Exception as e:
            node.status = AgentStatus.ERROR
            logger.error(f"[Orchestrator] Agent call failed: {agent_name}.{tool_name} - {e}")
            raise
    
    async def run_pipeline(self, initial_input: Dict[str, Any] = None) -> Dict[str, Dict[str, Any]]:
        """
        按顺序执行所有 Agent
        
        每个 Agent 的输出会传递给下一个 Agent
        """
        if self._execution_order:
            order = self._execution_order
        else:
            order = self._topological_sort()
        
        results = {}
        context = initial_input.copy() if initial_input else {}
        
        for agent_name in order:
            node = self._agents.get(agent_name)
            if not node or not node.mcp_server:
                continue
            
            tools = node.mcp_server.list_tools()
            if not tools:
                continue
            
            primary_tool = tools[0]
            
            result = await self.call_agent(
                agent_name,
                primary_tool.name,
                context
            )
            
            results[agent_name] = result
            
            if result.get("status") == "success":
                context["input"] = result.get("result")
        
        return results
    
    async def connect_to_agent(self, agent_name: str) -> None:
        """
        连接到指定 Agent（获取其 MCP 客户端）
        """
        await MCPConnectionManager.connect(agent_name)
        logger.info(f"[Orchestrator] Connected to agent: {agent_name}")
    
    async def disconnect_all(self) -> None:
        """
        断开所有 MCP 连接
        """
        await MCPConnectionManager.disconnect_all()
        logger.info("[Orchestrator] All connections disconnected")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取编排器状态
        """
        return {
            "orchestrator": self.name,
            "agents": {
                name: {
                    "status": node.status.value,
                    "description": node.description,
                    "dependencies": node.dependencies,
                    "tools": [t.name for t in node.mcp_server.list_tools()] if node.mcp_server else []
                }
                for name, node in self._agents.items()
            },
            "execution_order": self._execution_order,
            "mcp_connections": MCPConnectionManager.list_connections(),
            "available_agents": MCPConnectionManager.list_available_agents()
        }


def create_agent_with_mcp(
    name: str,
    agent: BaseAgent,
    tool_name: str = "run",
    tool_description: str = "",
    input_schema: Dict[str, Any] = None
) -> AgentNode:
    """
    快捷函数：创建一个带有 MCP Server 的 Agent
    
    自动将 Agent 的 run 方法暴露为 MCP 工具
    """
    server = MCPServer(name=name)
    
    @server.tool(
        name=tool_name,
        description=tool_description or f"Execute {name} agent",
        input_schema=input_schema or {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input for the agent"}
            }
        }
    )
    async def run_agent(input: str = "", **kwargs):
        if asyncio.iscoroutinefunction(agent.arun):
            return await agent.arun(input)
        else:
            return agent.run(input)
    
    return AgentNode(
        name=name,
        agent=agent,
        mcp_server=server
    )
