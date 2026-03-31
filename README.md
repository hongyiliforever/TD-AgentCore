# LangChain Agent Framework 设计文档

## 项目概述

本项目是一个基于 LangChain 框架构建的智能体开发框架，提供了完整的 Agent、Chain、Tool、BehaviorTree 和 API 模块，支持快速开发和部署智能对话应用。

## 目录结构

```
langchain-agent-framework/
├── src/                          # 源代码目录
│   ├── agents/                   # 智能体模块
│   │   ├── __init__.py
│   │   └── example_agent.py      # 示例智能体实现
│   ├── api/                      # API 接口模块
│   │   ├── __init__.py
│   │   └── example_api.py        # 示例 API 实现
│   ├── btree/                    # 行为树模块
│   │   ├── __init__.py
│   │   ├── behavior_tree.py      # 行为树核心实现
│   │   ├── visualizer.py         # 行为树可视化
│   │   ├── actions/              # 行为树动作
│   │   │   ├── __init__.py
│   │   │   └── example_actions.py
│   │   └── trees/                # 行为树JSON文件
│   │       └── example_workflow.json
│   ├── chains/                   # 链式调用模块
│   │   ├── __init__.py
│   │   └── base_chain.py         # 基础链和示例链
│   ├── config/                   # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py           # 全局配置
│   ├── core/                     # 核心功能模块
│   │   ├── __init__.py
│   │   └── database.py           # 数据库管理
│   ├── prompts/                  # Prompt 模板目录
│   │   └── example_prompts.md    # 示例 Prompt 模板
│   ├── tools/                    # 工具模块
│   │   ├── __init__.py
│   │   └── local_tools.py        # 本地工具定义
│   ├── utils/                    # 工具函数模块
│   │   ├── __init__.py
│   │   ├── logger.py             # 日志工具
│   │   └── prompt_util.py        # Prompt 加载工具
│   ├── __init__.py
│   ├── main.py                   # 应用入口
│   └── chat.py                   # 测试入口
├── docker/                       # Docker 部署配置
├── .env.example                  # 环境变量示例
├── pyproject.toml                # 项目配置
└── README.md                     # 项目说明
```

## 模块详解

### 1. config/ - 配置模块

配置模块负责管理应用程序的所有配置信息，使用 Pydantic Settings 进行配置管理。

**文件：`settings.py`**

```python
from src.config import settings

# 访问配置
print(settings.app.app_name)
print(settings.llm.model_name)
print(settings.openai_api_key)
```

**配置项说明：**

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `app.app_name` | 应用名称 | "LangChain Agent Framework" |
| `app.debug` | 调试模式 | False |
| `llm.model_name` | LLM 模型名称 | "gpt-4o-mini" |
| `llm.temperature` | 模型温度 | 0.7 |
| `database.host` | 数据库主机 | localhost |
| `database.port` | 数据库端口 | 5432 |

---

### 2. agents/ - 智能体模块

智能体模块提供了 Agent 的基础类和示例实现，支持对话历史管理和工具调用。

**基础类：`BaseAgent`**

```python
from src.agents import BaseAgent

class MyAgent(BaseAgent):
    name = "My Agent"
    description = "Custom agent"
    
    def run(self, input_text: str) -> str:
        messages = self._build_messages(input_text, "你是一个助手")
        response = self.llm.invoke(messages)
        return response.content
```

**示例智能体：`ExampleAgent`**

```python
from src.agents import ExampleAgent

agent = ExampleAgent()
response = agent.run("你好，请介绍一下自己")
print(response)

# 异步调用
response = await agent.arun("你好")
```

**工具智能体：`ToolAgent`**

```python
from src.agents import ToolAgent
from src.tools import get_default_tools

agent = ToolAgent(tools=get_default_tools())
response = agent.run("现在几点了？")
```

---

### 3. chains/ - 链式调用模块

链式调用模块提供了基于 Prompt Template 的处理链，支持自定义 Prompt 和输出解析。

**基础类：`BaseChain`**

```python
from src.chains import BaseChain

class MyChain(BaseChain):
    prompt_title = "自定义链"
    prompt_template = "请回答：{question}"
    
    def description(self) -> str:
        return "自定义处理链"
```

**示例链：`ExampleChain`**

```python
from src.chains import ExampleChain

chain = ExampleChain()
result = chain.run("什么是人工智能？")
print(result)
```

**信息提取链：`ExtractionChain`**

```python
from src.chains import ExtractionChain

chain = ExtractionChain()
result = chain.run("今天在北京召开了技术会议")
# 返回 JSON 格式的结构化信息
```

**多轮对话链：`ChatChain`**

```python
from src.chains import ChatChain

chain = ChatChain()
history = [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮你的？"}
]
result = chain.run(question="我刚才问了什么？", history=history)
```

---

### 4. btree/ - 行为树模块

行为树模块提供了基于 JSON 配置的工作流编排能力，支持本地加载和可视化。

**行为树 JSON 格式：**

```json
{
  "name": "example_workflow",
  "title": "示例工作流",
  "description": "一个简单的示例行为树",
  "type": "sequence",
  "children": [
    {
      "name": "check_input",
      "title": "检查输入",
      "type": "action",
      "func": {
        "type": "local",
        "schema": {
          "name": "check_input"
        }
      }
    },
    {
      "name": "process_selector",
      "title": "处理选择",
      "type": "selector",
      "children": [...]
    }
  ]
}
```

**节点类型说明：**

| 类型 | 说明 |
|------|------|
| `sequence` | 顺序执行，任一失败则停止 |
| `selector` | 选择执行，任一成功则停止 |
| `action` | 执行动作，调用注册的函数 |
| `condition` | 条件判断，返回成功或失败 |
| `parallel` | 并行执行，根据策略决定结果 |

**使用行为树：**

```python
from src.btree import BTreeRunner, action

# 定义动作
@action("my_action")
def my_action(context, **kwargs):
    # 处理逻辑
    return {"status": "success"}

# 加载并执行
runner = BTreeRunner()
runner.load_btree("src/btree/trees/example_workflow.json")
result = runner.run({"input": "Hello"})
```

**行为树可视化：**

```python
from src.btree import BTreeLoader, BTreeVisualizer

root = BTreeLoader.load_from_file("tree.json")
visualizer = BTreeVisualizer(root)
visualizer.save_html("tree_visualization.html")
```

**API 调用行为树：**

```python
import requests

# 执行行为树
response = requests.post("http://localhost:8000/api/btree/execute", json={
    "tree_name": "example_workflow",
    "inputs": {"input": "Hello", "fast_mode": False}
})

# 获取可视化
response = requests.get("http://localhost:8000/api/btree/example_workflow/visualize")
```

---

### 5. tools/ - 工具模块

工具模块提供了本地工具的定义和注册机制，支持 LangChain 的 Tool 接口。

**内置工具：**

| 工具名称 | 功能说明 |
|----------|----------|
| `get_current_time` | 获取当前时间 |
| `calculate` | 数学表达式计算 |
| `word_count` | 统计字数 |
| `reverse_string` | 反转字符串 |

**使用工具：**

```python
from src.tools import get_default_tools, LocalToolRegistry

# 获取所有默认工具
tools = get_default_tools()

# 注册自定义工具
from src.tools import create_custom_tool

def my_function(text: str) -> str:
    return text.upper()

tool = create_custom_tool(
    name="uppercase",
    description="将文本转换为大写",
    func=my_function
)
LocalToolRegistry.register(tool)
```

---

### 6. api/ - API 接口模块

API 模块基于 FastAPI 构建，提供 RESTful 接口供外部调用。

**启动服务：**

```bash
python -m src.main
# 或
uvicorn src.main:app --reload
```

**API 端点：**

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

**调用示例：**

```python
import requests

# 对话接口
response = requests.post("http://localhost:8000/api/chat", json={
    "message": "你好",
    "session_id": "test-session",
    "agent_type": "example"
})
print(response.json())

# 链执行接口
response = requests.post("http://localhost:8000/api/chain/run", json={
    "message": "今天天气晴朗",
    "chain_type": "extraction"
})
print(response.json())

# 行为树执行
response = requests.post("http://localhost:8000/api/btree/execute", json={
    "tree_name": "example_workflow",
    "inputs": {"input": "Hello", "fast_mode": False}
})
print(response.json())
```

---

### 7. core/ - 核心功能模块

核心功能模块提供数据库管理等基础功能。

**数据库管理：`DatabaseManager`**

```python
from src.core import DatabaseManager

db = DatabaseManager()

# 查询
results = db.execute_query("SELECT * FROM users WHERE id = %s", (1,))

# 插入
db.insert("users", {"name": "张三", "email": "zhangsan@example.com"})

# 查找
user = db.find_one("users", {"id": 1})
users = db.find_many("users", {"status": "active"}, limit=10)
```

---

### 8. utils/ - 工具函数模块

工具函数模块提供日志、Prompt 加载等通用功能。

**日志工具：**

```python
from src.utils import agent_logger

agent_logger.info("这是一条信息日志")
agent_logger.error("这是一条错误日志")
agent_logger.query_info(
    uuid="user-123",
    details={"action": "login"},
    step="authentication",
    message="用户登录成功"
)
```

**Prompt 加载工具：**

```python
from src.utils import PromptLoader

# 从 Markdown 文件加载 Prompt
prompt = PromptLoader.load_prompt("example_prompts.md", "示例对话")

# 获取可用的标题列表
titles = PromptLoader.get_available_titles("example_prompts.md")
```

---

### 9. prompts/ - Prompt 模板目录

Prompt 模板目录存放 Markdown 格式的 Prompt 模板文件，支持按一级标题分割。

**模板文件格式：**

```markdown
# 标题1

这是标题1下的 Prompt 内容...

# 标题2

这是标题2下的 Prompt 内容...
```

---

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
```

---

## 扩展开发

### 创建自定义 Agent

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

### 创建自定义 Chain

```python
from src.chains import BaseChain

class CustomChain(BaseChain):
    prompt_title = "自定义链"
    prompt_template = """你是一个专业分析师。
    
请分析以下内容：
{question}

请提供详细分析："""
    
    def description(self) -> str:
        return "自定义分析链"
```

### 创建自定义行为树动作

```python
from src.btree import action

@action("my_custom_action")
def my_custom_action(context, **kwargs):
    # 从上下文获取数据
    input_data = context.get("input")
    
    # 处理逻辑
    result = process(input_data)
    
    # 保存结果到上下文
    context.put("result", result)
    
    # 返回成功或失败
    return {"status": "success", "message": result}
```

### 创建自定义 Tool

```python
from src.tools import create_custom_tool, LocalToolRegistry

def my_custom_tool(input_text: str) -> str:
    # 自定义处理逻辑
    return f"处理结果: {input_text}"

tool = create_custom_tool(
    name="my_tool",
    description="自定义工具描述",
    func=my_custom_tool
)

LocalToolRegistry.register(tool)
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
│  │  - Example  │  │  - Example  │  │  - BTreeExecutor    │  │
│  │  - Tool     │  │  - Extract  │  │  - BTreeVisualizer  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                      Tools                               ││
│  │  - Local Tools  - Custom Tools  - Action Registry       ││
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
│  │  OpenAI API │  │  Database   │  │   JSON/MD Files     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 注意事项

1. **API Key 安全**：请勿将 API Key 提交到代码仓库，使用环境变量管理
2. **数据库连接**：确保数据库服务已启动并配置正确
3. **Prompt 模板**：Prompt 文件使用 UTF-8 编码，支持中文
4. **日志管理**：日志文件默认保存在 `logs/` 目录下
5. **行为树文件**：行为树 JSON 文件存放在 `src/btree/trees/` 目录
