# TD-AgentCore

## 项目概述

TD-AgentCore 是一个基于 LangChain 框架构建的智能体开发框架，核心设计理念是：

- **Agent 内部通过行为树（Behavior Tree）控制工作流**
- **多个 Agent 之间通过 MCP（Model Context Protocol）协议串联**

框架提供了完整的 Agent、Chain、Tool、BehaviorTree、MCP 和 API 模块，支持快速开发和部署智能对话应用。

## 核心架构（分层设计）

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP 层（Agent 间通信）                     │
│                                                              │
│   Agent A ◄──────── MCP ────────► Agent B                   │
│                                                              │
│   暴露的能力：research()、write()、review()                   │
│   （只暴露核心功能，不暴露内部实现）                           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Agent 内部（行为树 + 本地工具）                       │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              行为树工作流控制                         │   │
│   │                                                      │   │
│   │   check_input → process → output_result             │   │
│   │        │            │            │                  │   │
│   │        ▼            ▼            ▼                  │   │
│   │    本地函数      本地函数      本地函数               │   │
│   │    (不暴露)      (不暴露)      (不暴露)              │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
│   本地工具（不通过 MCP 暴露）：                                │
│   - get_current_time                                        │
│   - calculate                                               │
│   - web_search                                              │
│   - text_summarizer                                         │
└─────────────────────────────────────────────────────────────┘
```

### 分层原则

| 层级 | 内容 | 是否通过 MCP |
|------|------|--------------|
| **MCP 层** | Agent 之间的通信接口 | ✅ 是 |
| **Agent 层** | Agent 的核心能力入口 | ✅ 是（暴露） |
| **行为树层** | Agent 内部工作流控制 | ❌ 否（内部） |
| **本地工具层** | 行为树节点调用的函数 | ❌ 否（内部） |

## 目录结构

```
TD-AgentCore/
├── src/                          # 源代码目录
│   ├── agents/                   # 智能体模块
│   │   ├── __init__.py
│   │   ├── example_agent.py      # 基础智能体实现
│   │   └── specialized_agents.py # 专业智能体（研究、撰写、审核）
│   ├── api/                      # API 接口模块
│   │   ├── __init__.py
│   │   └── example_api.py        # API 实现
│   ├── btree/                    # 行为树模块（Agent 内部控制）
│   │   ├── __init__.py
│   │   ├── behavior_tree.py      # 行为树核心实现
│   │   ├── visualizer.py         # 行为树可视化
│   │   ├── actions/              # 行为树动作（本地函数）
│   │   │   ├── __init__.py
│   │   │   └── example_actions.py
│   │   └── trees/                # 行为树JSON文件
│   │       └── example_workflow.json
│   ├── chains/                   # 链式调用模块
│   │   ├── __init__.py
│   │   └── base_chain.py
│   ├── config/                   # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core/                     # 核心功能模块
│   │   ├── __init__.py
│   │   └── database.py
│   ├── mcp/                      # MCP 模块（Agent 间通信）
│   │   ├── __init__.py
│   │   ├── mcp_client.py         # MCP 客户端
│   │   ├── mcp_server.py         # MCP 服务端
│   │   └── orchestrator.py       # Agent 编排器
│   ├── prompts/                  # Prompt 模板目录
│   ├── tools/                    # 本地工具模块（不通过 MCP 暴露）
│   │   ├── __init__.py
│   │   └── local_tools.py
│   ├── utils/                    # 工具函数模块
│   ├── main.py                   # 应用入口
│   ├── chat.py                   # 测试入口
│   └── mcp_demo.py               # MCP 分层架构演示
├── docker/                       # Docker 部署配置
├── .env.example                  # 环境变量示例
├── pyproject.toml                # 项目配置
└── README.md                     # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 3. 运行服务

```bash
# 启动 API 服务
python -m src.main

# 或运行测试
python -m src.chat

# 运行 MCP 分层架构演示
python -m src.mcp_demo
```

---

## 模块详解

### 1. MCP 模块（Agent 间通信）

MCP 只用于 Agent 之间的通信，不涉及 Agent 内部实现。

#### MCP Server - 暴露 Agent 能力

```python
from src.mcp import MCPServer
from src.agents import ResearcherAgent

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
    agent = ResearcherAgent()
    result = await agent.arun(topic)
    return result
```

#### Agent 编排器 - 管理多 Agent 协作

```python
from src.mcp import AgentOrchestrator

orchestrator = AgentOrchestrator(name="ContentPipeline")

# 注册 Agent（每个 Agent 有自己的 MCP Server）
orchestrator.register_agent(
    name="researcher",
    mcp_server=researcher_server,
    description="研究员智能体"
)

orchestrator.register_agent(
    name="writer",
    mcp_server=writer_server,
    description="撰写智能体",
    dependencies=["researcher"]  # 依赖研究员
)

# 设置执行顺序
orchestrator.set_execution_order(["researcher", "writer", "reviewer"])

# 通过 MCP 调用 Agent
result = await orchestrator.call_agent(
    "researcher",
    "research",
    {"topic": "人工智能"}
)
```

#### 快速创建带 MCP 的 Agent

```python
from src.mcp import create_agent_with_mcp
from src.agents import ResearcherAgent

agent = ResearcherAgent()

node = create_agent_with_mcp(
    name="researcher",
    agent=agent,
    tool_name="research",
    tool_description="研究工具"
)

# 然后注册到编排器
orchestrator.register_agent(name="researcher", mcp_server=node.mcp_server)
```

---

### 2. 行为树模块（Agent 内部控制）

行为树用于控制 Agent **内部**的工作流程，不通过 MCP 暴露。

#### 节点类型

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| `sequence` | 顺序执行，任一失败则停止 | 需要按顺序完成的任务 |
| `selector` | 选择执行，任一成功则停止 | 多种备选方案 |
| `action` | 执行动作 | 具体的业务逻辑 |
| `condition` | 条件判断 | 分支判断 |
| `parallel` | 并行执行 | 需要同时执行的任务 |

#### 定义内部函数（不暴露给 MCP）

```python
from src.btree import action
from src.btree.behavior_tree import BTreeContext

# 这些是 Agent 内部使用的函数，不通过 MCP 暴露
@action("internal_check_input")
def check_input(context: BTreeContext, **kwargs):
    """内部函数：检查输入 - 不暴露给 MCP"""
    input_data = context.get("input")
    if input_data:
        return {"status": "success"}
    return {"status": "failure"}

@action("internal_process")
def process(context: BTreeContext, **kwargs):
    """内部函数：处理数据 - 不暴露给 MCP"""
    input_data = context.get("input")
    # 处理逻辑...
    context.put("result", processed_data)
    return {"status": "success"}
```

#### 使用行为树

```python
from src.btree import BTreeRunner

runner = BTreeRunner()
runner.load_btree("src/btree/trees/example_workflow.json")
result = runner.run({"input": "Hello"})
```

---

### 3. 智能体模块

#### 内置智能体

| Agent | 功能说明 |
|-------|----------|
| `BaseAgent` | 基础智能体类 |
| `ExampleAgent` | 示例智能体 |
| `ToolAgent` | 可使用工具的智能体 |
| `ResearcherAgent` | 研究员智能体 |
| `WriterAgent` | 撰写智能体 |
| `ReviewerAgent` | 审核智能体 |

#### 创建自定义 Agent

```python
from src.agents import BaseAgent

class CustomAgent(BaseAgent):
    name = "Custom Agent"
    description = "自定义智能体"
    
    SYSTEM_PROMPT = "你是一个专业的助手..."
    
    def run(self, input_text: str) -> str:
        messages = self._build_messages(input_text, self.SYSTEM_PROMPT)
        response = self.llm.invoke(messages)
        self.add_to_history("user", input_text)
        self.add_to_history("assistant", response.content)
        return response.content
```

---

### 4. 本地工具模块

本地工具是 Agent **内部**使用的函数，不通过 MCP 暴露。

#### 内置工具

| 工具名称 | 功能说明 |
|----------|----------|
| `get_current_time` | 获取当前时间 |
| `calculate` | 数学表达式计算 |
| `word_count` | 统计字数 |
| `reverse_string` | 反转字符串 |

#### 创建自定义工具

```python
from src.tools import create_custom_tool, LocalToolRegistry

def my_function(input_text: str) -> str:
    return input_text.upper()

tool = create_custom_tool(
    name="uppercase",
    description="将文本转换为大写",
    func=my_function
)
LocalToolRegistry.register(tool)
```

---

### 5. API 模块

#### 启动服务

```bash
python -m src.main
# 或
uvicorn src.main:app --reload
```

#### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/chat` | POST | 对话接口 |
| `/api/chain/run` | POST | 链执行接口 |
| `/api/btree/execute` | POST | 行为树执行 |
| `/api/btree/list` | GET | 行为树列表 |
| `/api/btree/{name}/visualize` | GET | 行为树可视化 |
| `/api/agents` | GET | 获取可用 Agent 列表 |
| `/api/chains` | GET | 获取可用 Chain 列表 |

---

## 多 Agent 协作示例

### 场景：内容生产流水线

```
用户输入主题
    │
    ▼
┌─────────────────┐
│ ResearcherAgent │  研究主题，收集信息
│                 │
│ MCP 暴露:       │
│   research()    │
│                 │
│ 内部（不暴露）:  │
│   行为树控制    │
│   本地工具      │
└────────┬────────┘
         │ MCP 调用
         │ research(topic)
         ▼
┌─────────────────┐
│  WriterAgent    │  根据研究结果撰写内容
│                 │
│ MCP 暴露:       │
│   write()       │
└────────┬────────┘
         │ MCP 调用
         │ write(research_result)
         ▼
┌─────────────────┐
│ ReviewerAgent   │  审核内容，提供改进建议
│                 │
│ MCP 暴露:       │
│   review()      │
└────────┬────────┘
         │
         ▼
    最终输出
```

### 完整代码示例

```python
import asyncio
from src.mcp import MCPServer, AgentOrchestrator, create_agent_with_mcp
from src.agents import ResearcherAgent, WriterAgent, ReviewerAgent

async def main():
    # 创建编排器
    orchestrator = AgentOrchestrator(name="ContentPipeline")
    
    # 创建并注册 Agent（每个 Agent 自动暴露 MCP 接口）
    researcher_node = create_agent_with_mcp(
        name="researcher",
        agent=ResearcherAgent(),
        tool_name="research",
        tool_description="研究主题"
    )
    orchestrator.register_agent(name="researcher", mcp_server=researcher_node.mcp_server)
    
    writer_node = create_agent_with_mcp(
        name="writer",
        agent=WriterAgent(),
        tool_name="write",
        tool_description="撰写文章"
    )
    orchestrator.register_agent(name="writer", mcp_server=writer_node.mcp_server)
    
    reviewer_node = create_agent_with_mcp(
        name="reviewer",
        agent=ReviewerAgent(),
        tool_name="review",
        tool_description="审核文章"
    )
    orchestrator.register_agent(name="reviewer", mcp_server=reviewer_node.mcp_server)
    
    # 设置执行顺序
    orchestrator.set_execution_order(["researcher", "writer", "reviewer"])
    
    # 执行流水线
    results = await orchestrator.run_pipeline({"input": "量子计算的应用前景"})
    print(results)

asyncio.run(main())
```

---

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  /api/chat  │  │ /api/chain  │  │  /api/btree         │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼───────────────────┼──────────────┘
          │                │                   │
          ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      Business Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Agents    │  │   Chains    │  │    BehaviorTree     │  │
│  │  - Base     │  │  - Base     │  │  - BTreeRunner      │  │
│  │  - Research │  │  - Extract  │  │  - BTreeExecutor    │  │
│  │  - Writer   │  │  - Chat     │  │  - Actions(内部)    │  │
│  │  - Reviewer │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                      MCP Layer                           ││
│  │  - MCPClient  - MCPServer  - AgentOrchestrator          ││
│  │  (只用于 Agent 间通信，不涉及内部实现)                    ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │                Local Tools (内部使用)                    ││
│  │  - get_current_time  - calculate  - word_count          ││
│  │  (不通过 MCP 暴露)                                       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
          │                │                   │
          ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Config    │  │  Database   │  │      Utils          │  │
│  │  - Settings │  │  - Manager  │  │  - Logger           │  │
│  │  - LLM      │  │  - Core     │  │  - Prompt Loader    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  OpenAI API │  │  Database   │  │   External MCP      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 注意事项

1. **API Key 安全**：请勿将 API Key 提交到代码仓库，使用环境变量管理
2. **分层原则**：
   - MCP 只用于 Agent 间通信
   - 行为树和本地工具是 Agent 内部实现，不通过 MCP 暴露
3. **数据库连接**：确保数据库服务已启动并配置正确
4. **Prompt 模板**：Prompt 文件使用 UTF-8 编码，支持中文
5. **日志管理**：日志文件默认保存在 `logs/` 目录下

---

## 扩展开发

### 添加新的 MCP 工具（暴露 Agent 能力）

```python
from src.mcp import MCPServer

server = MCPServer(name="my_agent")

@server.tool(
    name="my_capability",
    description="Agent 的核心能力",
    input_schema={
        "type": "object",
        "properties": {
            "input": {"type": "string"}
        }
    }
)
async def my_capability(input: str) -> str:
    # 调用 Agent 内部逻辑
    return f"处理结果: {input}"
```

### 添加新的行为树动作（内部使用）

```python
from src.btree import action

@action("internal_action")
def internal_action(context, **kwargs):
    """
    内部函数 - 不通过 MCP 暴露
    只在行为树内部使用
    """
    input_data = context.get("input")
    result = process(input_data)
    context.put("result", result)
    return {"status": "success"}
```

---

## License

MIT License
