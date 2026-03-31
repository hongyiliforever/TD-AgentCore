"""
TD-AgentCore 正确分层架构演示

架构说明：
┌─────────────────────────────────────────────────────────────┐
│                    MCP 层（Agent 间通信）                     │
│                                                              │
│   Agent A ◄──────── MCP ────────► Agent B                   │
│                                                              │
│   暴露的能力：research()、write()、review()                   │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Agent 内部（行为树 + 本地工具）                       │
│                                                              │
│   行为树控制：check_input → process → output                 │
│   本地工具：web_search、text_summarizer（不暴露）             │
└─────────────────────────────────────────────────────────────┘
"""

import asyncio
import os

from src.agents.specialized_agents import ResearcherAgent, WriterAgent, ReviewerAgent
from src.btree import BTreeRunner, action
from src.btree.behavior_tree import BTreeContext
from src.mcp import (
    MCPServer,
    AgentOrchestrator,
    MCPConnectionManager,
    create_agent_with_mcp
)
from src.utils.logger import agent_logger as logger


# ============================================================
# 第一部分：Agent 内部工具（不通过 MCP 暴露）
# ============================================================

@action("internal_check_input")
def internal_check_input(context: BTreeContext, **kwargs):
    """内部函数：检查输入 - 不暴露给 MCP"""
    input_data = context.get("input")
    has_input = input_data is not None and len(str(input_data)) > 0
    
    logger.info(f"[内部函数] 检查输入: {has_input}")
    
    if has_input:
        return {"status": "success", "message": "输入有效"}
    return {"status": "failure", "message": "无输入"}


@action("internal_process")
def internal_process(context: BTreeContext, **kwargs):
    """内部函数：处理数据 - 不暴露给 MCP"""
    input_data = context.get("input")
    
    logger.info(f"[内部函数] 处理数据: {str(input_data)[:50]}...")
    
    processed = f"[已处理] {input_data}"
    context.put("processed_data", processed)
    
    return {"status": "success", "message": "处理完成"}


@action("internal_output")
def internal_output(context: BTreeContext, **kwargs):
    """内部函数：输出结果 - 不暴露给 MCP"""
    result = context.get("processed_data", "无结果")
    
    logger.info(f"[内部函数] 输出结果: {result[:50]}...")
    
    context.put("final_result", result)
    return {"status": "success", "message": result}


# ============================================================
# 第二部分：MCP Server - 暴露 Agent 能力（给其他 Agent 调用）
# ============================================================

def create_researcher_mcp_server():
    """
    创建研究员 Agent 的 MCP Server
    
    只暴露 Agent 的核心功能，不暴露内部实现
    """
    server = MCPServer(name="researcher_agent")
    
    @server.tool(
        name="research",
        description="研究指定主题并返回结果",
        input_schema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "研究主题"}
            },
            "required": ["topic"]
        }
    )
    async def research(topic: str) -> str:
        """
        MCP 暴露的工具：研究主题
        
        内部会调用 Agent，Agent 内部可能使用行为树
        但这些内部实现对外不可见
        """
        logger.info(f"[MCP 工具] research 被调用: {topic}")
        
        agent = ResearcherAgent()
        result = await agent.arun(topic)
        
        return result
    
    @server.resource(
        uri="info://researcher",
        name="研究员信息",
        description="获取研究员 Agent 的信息"
    )
    def get_info() -> str:
        return "ResearcherAgent - 负责信息收集和研究"
    
    return server


def create_writer_mcp_server():
    """创建撰写 Agent 的 MCP Server"""
    server = MCPServer(name="writer_agent")
    
    @server.tool(
        name="write",
        description="根据研究结果撰写文章",
        input_schema={
            "type": "object",
            "properties": {
                "research_result": {"type": "string", "description": "研究结果"}
            },
            "required": ["research_result"]
        }
    )
    async def write(research_result: str) -> str:
        logger.info(f"[MCP 工具] write 被调用")
        
        agent = WriterAgent()
        result = await agent.arun(f"请根据以下研究结果撰写文章：\n{research_result}")
        
        return result
    
    return server


def create_reviewer_mcp_server():
    """创建审核 Agent 的 MCP Server"""
    server = MCPServer(name="reviewer_agent")
    
    @server.tool(
        name="review",
        description="审核文章并提供改进建议",
        input_schema={
            "type": "object",
            "properties": {
                "article": {"type": "string", "description": "待审核的文章"}
            },
            "required": ["article"]
        }
    )
    async def review(article: str) -> str:
        logger.info(f"[MCP 工具] review 被调用")
        
        agent = ReviewerAgent()
        result = await agent.arun(f"请审核以下文章并提供改进建议：\n{article}")
        
        return result
    
    return server


# ============================================================
# 第三部分：演示 - 正确的分层架构
# ============================================================

async def demo_layered_architecture():
    """
    演示正确的分层架构
    """
    logger.info("\n" + "=" * 60)
    logger.info("演示：正确的分层架构")
    logger.info("=" * 60)
    
    # 1. 创建 MCP Servers（暴露 Agent 能力）
    logger.info("\n[步骤1] 创建 MCP Servers - 暴露 Agent 能力")
    
    researcher_server = create_researcher_mcp_server()
    writer_server = create_writer_mcp_server()
    reviewer_server = create_reviewer_mcp_server()
    
    logger.info(f"  - ResearcherAgent 暴露工具: {[t.name for t in researcher_server.list_tools()]}")
    logger.info(f"  - WriterAgent 暴露工具: {[t.name for t in writer_server.list_tools()]}")
    logger.info(f"  - ReviewerAgent 暴露工具: {[t.name for t in reviewer_server.list_tools()]}")
    
    # 2. 创建编排器并注册 Agent
    logger.info("\n[步骤2] 创建编排器并注册 Agent")
    
    orchestrator = AgentOrchestrator(name="ContentPipeline")
    
    orchestrator.register_agent(
        name="researcher",
        mcp_server=researcher_server,
        description="研究员智能体"
    )
    
    orchestrator.register_agent(
        name="writer",
        mcp_server=writer_server,
        description="撰写智能体",
        dependencies=["researcher"]
    )
    
    orchestrator.register_agent(
        name="reviewer",
        mcp_server=reviewer_server,
        description="审核智能体",
        dependencies=["writer"]
    )
    
    orchestrator.set_execution_order(["researcher", "writer", "reviewer"])
    
    # 3. 通过 MCP 调用 Agent
    logger.info("\n[步骤3] 通过 MCP 调用 Agent（Agent 间通信）")
    
    topic = "人工智能在教育领域的应用"
    
    # 调用研究员
    logger.info(f"\n  调用 researcher.research('{topic}')")
    research_result = await orchestrator.call_agent(
        "researcher",
        "research",
        {"topic": topic}
    )
    logger.info(f"  研究结果: {research_result.get('result', '')[:100]}...")
    
    # 调用撰写者
    logger.info(f"\n  调用 writer.write(...)")
    write_result = await orchestrator.call_agent(
        "writer",
        "write",
        {"research_result": research_result.get("result", "")}
    )
    logger.info(f"  撰写结果: {write_result.get('result', '')[:100]}...")
    
    # 调用审核者
    logger.info(f"\n  调用 reviewer.review(...)")
    review_result = await orchestrator.call_agent(
        "reviewer",
        "review",
        {"article": write_result.get("result", "")}
    )
    logger.info(f"  审核结果: {review_result.get('result', '')[:100]}...")
    
    # 4. 展示分层架构
    logger.info("\n[步骤4] 分层架构总结")
    
    status = orchestrator.get_status()
    logger.info(f"  编排器: {status['orchestrator']}")
    logger.info(f"  可用 Agent: {status['available_agents']}")
    logger.info(f"  执行顺序: {status['execution_order']}")
    
    return orchestrator


async def demo_internal_tools():
    """
    演示 Agent 内部工具（不通过 MCP 暴露）
    """
    logger.info("\n" + "=" * 60)
    logger.info("演示：Agent 内部工具（不通过 MCP 暴露）")
    logger.info("=" * 60)
    
    logger.info("\n这些内部函数不会暴露给 MCP：")
    logger.info("  - internal_check_input: 检查输入")
    logger.info("  - internal_process: 处理数据")
    logger.info("  - internal_output: 输出结果")
    
    logger.info("\n它们只能在行为树内部使用：")
    
    btree_json = """
    {
        "name": "internal_workflow",
        "type": "sequence",
        "children": [
            {
                "name": "check",
                "type": "action",
                "func": {"type": "local", "schema": {"name": "internal_check_input"}}
            },
            {
                "name": "process",
                "type": "action",
                "func": {"type": "local", "schema": {"name": "internal_process"}}
            },
            {
                "name": "output",
                "type": "action",
                "func": {"type": "local", "schema": {"name": "internal_output"}}
            }
        ]
    }
    """
    
    from src.btree.behavior_tree import BTreeLoader
    import json
    
    runner = BTreeRunner()
    root = BTreeLoader.load_from_json(btree_json)
    runner.root = root
    
    result = runner.run({"input": "测试数据"})
    
    logger.info(f"\n行为树执行结果: {result['status']}")
    logger.info(f"最终结果: {result['context']['data'].get('final_result', '无')}")


async def demo_quick_create():
    """
    演示快速创建带 MCP 的 Agent
    """
    logger.info("\n" + "=" * 60)
    logger.info("演示：快速创建带 MCP 的 Agent")
    logger.info("=" * 60)
    
    agent = ResearcherAgent()
    
    node = create_agent_with_mcp(
        name="quick_researcher",
        agent=agent,
        tool_name="research",
        tool_description="快速研究工具"
    )
    
    orchestrator = AgentOrchestrator(name="QuickDemo")
    orchestrator.register_agent(
        name="quick_researcher",
        mcp_server=node.mcp_server
    )
    
    result = await orchestrator.call_agent(
        "quick_researcher",
        "research",
        {"input": "量子计算"}
    )
    
    logger.info(f"结果: {result.get('result', '')[:100]}...")


async def main():
    logger.info("\n" + "=" * 60)
    logger.info("TD-AgentCore 分层架构演示")
    logger.info("=" * 60)
    
    logger.info("\n架构说明：")
    logger.info("┌─────────────────────────────────────────┐")
    logger.info("│     MCP 层（Agent 间通信）              │")
    logger.info("│   Agent A ◄──────► Agent B              │")
    logger.info("│   暴露：research()、write()             │")
    logger.info("└─────────────────────────────────────────┘")
    logger.info("              │")
    logger.info("              ▼")
    logger.info("┌─────────────────────────────────────────┐")
    logger.info("│   Agent 内部（行为树 + 本地工具）        │")
    logger.info("│   内部函数（不暴露）                    │")
    logger.info("└─────────────────────────────────────────┘")
    
    await demo_layered_architecture()
    await demo_internal_tools()
    await demo_quick_create()
    
    logger.info("\n" + "=" * 60)
    logger.info("演示完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
