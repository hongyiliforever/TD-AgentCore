# TD-AgentCore

## 项目概述

TD-AgentCore 是一个企业级智能体开发框架，核心设计理念：

- **Agent 内部通过行为树（Behavior Tree）控制工作流**
- **多个 Agent 之间通过 MCP（Model Context Protocol）协议串联**
- **云原生微服务架构，支持 Docker/Kubernetes 部署**
- **状态持久化，支持断点续传**
- **LLM 网关，支持多模型路由与降级**

## 企业级架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx 网关                            │
│              (负载均衡 + 限流 + SSL 终止)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                            │
│                  (FastAPI + 认证 + 路由)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator                           │
│           (任务编排 + MCP 路由 + 状态管理)                  │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ Researcher  │   │   Writer    │   │  Reviewer   │
    │   Agent     │   │   Agent     │   │   Agent     │
    │  (Docker)   │   │  (Docker)   │   │  (Docker)   │
    └─────────────┘   └─────────────┘   └─────────────┘
            │                 │                 │
            └─────────────────┼─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据层                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │ PostgreSQL  │   │   Redis     │   │  pgvector   │       │
│  │ (状态持久化)│   │  (缓存)     │   │ (向量存储)  │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
TD-AgentCore/
├── docker/                       # Docker 配置
│   ├── Dockerfile.api           # API 网关镜像
│   ├── Dockerfile.orchestrator  # 编排器镜像
│   ├── Dockerfile.agent         # Agent 镜像
│   ├── entrypoint.sh            # 容器入口脚本
│   ├── init-db.sql              # 数据库初始化
│   └── nginx/
│       └── nginx.conf           # Nginx 配置
├── src/
│   ├── agents/                  # 智能体模块
│   ├── api/                     # API 接口
│   ├── btree/                   # 行为树模块
│   ├── chains/                  # 链式调用
│   ├── config/                  # 配置管理
│   ├── core/                    # 核心功能
│   ├── mcp/                     # MCP 协议（Agent 间通信）
│   ├── services/                # 企业级服务
│   │   ├── state_store.py       # 状态存储（PostgreSQL + Redis）
│   │   ├── task_manager.py      # 任务管理器
│   │   ├── llm_gateway.py       # LLM 网关
│   │   ├── http_mcp_server.py   # HTTP MCP 服务端
│   │   ├── http_mcp_client.py   # HTTP MCP 客户端
│   │   ├── orchestrator_service.py  # 编排器服务
│   │   ├── agent_service.py     # Agent 服务
│   │   └── tracing.py           # 全链路追踪
│   ├── tools/                   # 本地工具
│   ├── utils/                   # 工具函数
│   └── main.py                  # 应用入口
├── docker-compose.yml           # Docker 编排
├── pyproject.toml               # 项目配置
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/your-repo/TD-AgentCore.git
cd TD-AgentCore

# 安装依赖
pip install -e .

# 复制环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 2. 启动服务

**开发模式（单进程）：**

```bash
python -m src.main
```

**生产模式（Docker）：**

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| API 网关 | http://localhost:80 | Nginx 代理 |
| API 文档 | http://localhost:80/docs | Swagger UI |
| 编排器 | http://localhost:8001 | 任务编排 |
| Researcher | http://localhost:8002 | 研究员 Agent |
| Writer | http://localhost:8003 | 撰写 Agent |
| Reviewer | http://localhost:8004 | 审核 Agent |

---

## 核心功能

### 1. 状态持久化与断点续传

```python
from src.services.state_store import get_state_store

state_store = await get_state_store()

# 创建任务
task = await state_store.create_task(
    task_type="pipeline",
    input_data={"input": "研究 AI 发展"},
    total_steps=3
)

# 更新状态
await state_store.update_task_status(
    task_id=task.id,
    status="running",
    progress=50,
    current_step="executing writer"
)

# 断点续传：获取任务状态后恢复执行
task = await state_store.get_task(task_id)
if task.status == "paused":
    # 从断点恢复
    await resume_from_checkpoint(task)
```

### 2. LLM 网关（模型路由与降级）

```python
from src.services.llm_gateway import init_llm_gateway, TaskComplexity

gateway = await init_llm_gateway()

# 自动选择模型（简单任务用小模型，复杂任务用大模型）
response = await gateway.invoke(
    messages=messages,
    complexity=TaskComplexity.COMPLEX  # 自动选择 gpt-4o
)

# 手动指定模型
response = await gateway.invoke(
    messages=messages,
    model_name="gpt-4o-mini"
)

# 流式输出
async for chunk in gateway.stream(messages):
    print(chunk)
```

### 3. HTTP MCP 通信

```python
from src.services.http_mcp_client import MCPClientPool

# 调用其他 Agent
response = await MCPClientPool.call_tool(
    agent_name="researcher",
    tool_name="run",
    arguments={"input": "AI 发展历史"},
    trace_id="trace-123"
)

print(response.result)
```

### 4. 任务管理

```python
from src.services.task_manager import get_task_manager

task_manager = await get_task_manager()

# 提交异步任务
task_id = await task_manager.submit_task(
    task_type="pipeline",
    input_data={"input": "研究量子计算"},
    total_steps=3
)

# 查询状态
result = await task_manager.get_task_status(task_id)
print(result.status, result.progress)

# 取消任务
await task_manager.cancel_task(task_id)

# 断点续传
await task_manager.resume_task(task_id)
```

### 5. 全链路追踪

```python
from src.services.tracing import get_tracer, traced

tracer = get_tracer()

# 开始追踪
span = tracer.start_trace("my_operation")

# 添加标签和日志
span.add_tag("user_id", "user-123")
span.add_log("Processing step 1")

# 结束追踪
tracer.finish_span(span)

# 使用装饰器
@traced("my_function")
async def my_function():
    # 自动追踪
    pass
```

---

## API 接口

### 任务管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/pipeline` | POST | 创建执行流水线 |
| `/api/pipeline/{task_id}` | GET | 获取任务状态 |
| `/api/pipeline/{task_id}/cancel` | POST | 取消任务 |
| `/api/pipeline/{task_id}/resume` | POST | 恢复任务 |
| `/sse/pipeline/{task_id}` | GET | SSE 流式状态 |

### Agent 调用

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agents` | GET | 列出可用 Agent |
| `/api/agents/call` | POST | 直接调用 Agent |
| `/api/agents/{name}/tools` | GET | 获取 Agent 工具列表 |
| `/api/agents/{name}/call` | POST | 调用 Agent 工具 |

---

## 配置说明

### 环境变量

```bash
# 数据库
DATABASE_URL=postgresql://agentcore:agentcore123@postgres:5432/agentcore
REDIS_URL=redis://redis:6379/0

# LLM
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1

# Agent 模型配置
RESEARCHER_MODEL=gpt-4o-mini
WRITER_MODEL=gpt-4o-mini
REVIEWER_MODEL=gpt-4o-mini

# 服务端口
API_PORT=8000
ORCHESTRATOR_PORT=8001
RESEARCHER_PORT=8002
WRITER_PORT=8003
REVIEWER_PORT=8004
```

### Docker 资源配置

在 `docker-compose.yml` 中可以为不同 Agent 配置资源限制：

```yaml
researcher-agent:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
```

---

## 扩展开发

### 添加新的 Agent

1. 创建 Agent 类：

```python
# src/agents/my_agent.py
from src.agents import BaseAgent

class MyAgent(BaseAgent):
    name = "My Agent"
    
    def run(self, input_text: str) -> str:
        # 实现逻辑
        return result
```

2. 添加 Docker 服务：

```yaml
# docker-compose.yml
my-agent:
  build:
    context: .
    dockerfile: docker/Dockerfile.agent
  environment:
    - AGENT_NAME=my_agent
    - AGENT_TYPE=my
  ports:
    - "8005:8002"
```

### 添加新的行为树动作

```python
from src.btree import action

@action("my_action")
def my_action(context, **kwargs):
    # 内部实现，不通过 MCP 暴露
    result = process(context.get("input"))
    context.put("result", result)
    return {"status": "success"}
```

---

## 监控与运维

### 健康检查

```bash
# 检查所有服务
curl http://localhost/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### 日志查看

```bash
# Docker 日志
docker-compose logs -f orchestrator
docker-compose logs -f researcher-agent
```

### 性能指标

```bash
# 获取统计信息
curl http://localhost:8001/stats
```

---

## License

MIT License
