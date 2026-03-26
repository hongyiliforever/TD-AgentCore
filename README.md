# td-js-copilot-gpt

IoT Copilot GPT - 质差定界派单智能体服务

## 项目简介

本项目是基于 an-copilot 框架开发的智能工单处理系统，主要用于**质差定界派单**场景。通过智能体自动化完成质差识别检测、预警聚合、智能定界定位分析等核心业务流程。

### 核心功能

- **质差识别检测**: 根据指标阈值规则自动识别质差时段
- **质差预警与聚合**: 基于预警规则触发预警并生成预警工单
- **智能定界定位分析**: 通过错误码分析、聚类分析定位问题根因

## 技术栈

- Python 3.11
- an-copilot 3.0.0
- FastAPI
- PostgreSQL
- Docker

## 项目结构

```
td-js-copilot-gpt/
├── docker/                    # Docker 配置
│   ├── Dockerfile
│   ├── build.sh
│   ├── startup.sh
│   └── td-js-copilot-gpt.yml
├── docs/                      # 文档
│   ├── 数据库/
│   │   └── 建表.sql
│   └── 质差定界/
│       ├── 质差定界派单_工具设计文档.md
│       └── 质差定界派单_行为树.json
├── src/                       # 源代码
│   ├── agents/               # 智能体
│   │   └── quality_defect/
│   │       ├── quality_defect_agent.py
│   │       ├── quality_defect_runner.py
│   │       └── extract_elements_chain.py
│   ├── api/                  # API 接口
│   │   └── quality_defect_api.py
│   ├── config/               # 配置
│   │   ├── settings.py
│   │   └── config.json
│   ├── core/                 # 核心业务
│   │   ├── order/
│   │   │   └── order_query.py
│   │   └── quality_defect/
│   │       └── quality_defect_db.py
│   ├── knowledges/           # 知识库
│   │   └── reply_prompt.md
│   ├── utils/                # 工具函数
│   ├── main.py               # 入口文件
│   └── chat.py               # Streamlit 聊天界面
├── Makefile
├── pyproject.toml
└── README.md
```

## 前置条件

- Python >=3.11, <3.12
- Makefile (可选，Windows 可直接使用命令)

## 快速开始

### 第一步：下载代码

```bash
git clone <repository_url>
cd td-js-copilot-gpt
```

### 第二步：创建虚拟环境

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
python -V
```

### 第三步：配置环境变量

在项目根目录下创建 `.env` 文件：

```shell
# 模型地址配置
DEFAULT_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DEFAULT_API_KEY=sk-xxx
LLM_ID=qwen2-72b

# CES 服务地址配置
CES_ENABLED=false
CES_URI=http://10.19.83.184:6066
CES_HEARTBEAT_SOURCE_HOST=127.0.0.1
CES_HEARTBEAT_SOURCE_PORT=5000

# 开启 SWAGGER
SWAGGER_UI_ENABLED=true

# 质差定界行为树编码
quality_defect_btree_code=your_btree_code
```

### 第四步：安装依赖并运行

**Linux/macOS:**

```bash
make init
make run
```

**Windows (无 Make 环境):**

```powershell
# 安装依赖
pip install . .[lint] .[test] .[package] --trusted-host 10.1.207.194 --default-timeout=600 --extra-index-url http://10.1.207.194:8099/nexus/repository/pypi-group/simple/ -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 运行服务
python src/main.py -H 0.0.0.0 -P 5000
```

## API 接口

服务启动后，访问 `http://localhost:5000/docs` 查看 Swagger API 文档。

### 质差定界派单接口

#### 1. 质差识别检测

```bash
POST /api/quality_defect/detect_anomaly
```

请求示例：

```json
{
  "order_id": "ORDER-001"
}
```

#### 2. 质差预警与聚合

```bash
POST /api/quality_defect/generate_anomaly_alert
```

请求示例：

```json
{
  "order_id": "ORDER-001",
  "indicator_name": "寻呼成功率",
  "defect_count": 2,
  "defect_periods_str": "2026-01-28 11:00、2026-01-28 13:00"
}
```

#### 3. 智能定界定位分析

```bash
POST /api/quality_defect/execute_fault_localization
```

请求示例：

```json
{
  "order_id": "ORDER-001",
  "alert_id": "WARN-2026012804",
  "indicator_name": "寻呼成功率",
  "defect_periods_str": "2个 (11:00/13:00)"
}
```

### Agent 消息接口

```bash
POST /v1/api/agent-message
```

请求示例：

```json
{
  "name": "质差定界派单智能体",
  "query": "{\"order_id\": \"ORDER-001\"}",
  "response_mode": "blocking",
  "session_id": "af56d032-22bb-4585-98ae-f624510acc32",
  "request_id": "a3712e54-e3b-480b-8179-1fad6fd044c3",
  "user": "user"
}
```

## 内嵌 CHAT 窗口

基于 Streamlit 构建的测试界面：

```bash
make chat
# 或
streamlit run src/chat.py --server.address=127.0.0.1 --server.port=5000
```

## 配置参数

### 模型配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `DEFAULT_API_BASE` | 大模型 API 地址 | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| `DEFAULT_API_KEY` | API 密钥 | - |
| `LLM_ID` | 模型 ID | qwen2-72b |
| `LLM_TEMPERATURE` | 温度参数 | 0.00000001 |
| `LLM_MAX_TOKENS` | 最大 Token 数 | 2048 |

### 服务配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `CES_ENABLED` | 是否启用 CES 服务 | false |
| `CES_URI` | CES 服务地址 | - |
| `SWAGGER_UI_ENABLED` | 是否开启 Swagger | false |
| `WEB_CONCURRENCY` | FastAPI 工作进程数 | 1 |

### 安全配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `SECURITY_ENABLED` | 是否启用安全认证 | false |
| `SECURITY_API_SECRET_KEY` | API 密钥 | 随机生成 |
| `OAUTH_ENABLED` | 是否启用 OAuth | false |

### 护栏配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `GUARDRAIL_INPUT_ENABLED` | 输入护栏 | true |
| `GUARDRAIL_OUTPUT_ENABLED` | 输出护栏 | false |
| `GUARDRAIL_SENSITIVE_WORDS_FILE` | 敏感词文件 | - |

## 常用命令

```bash
make init       # 初始化环境
make run        # 启动服务
make chat       # 启动聊天服务
make lint       # 代码规范检查
make fmt        # 代码格式化
make coverage   # 测试覆盖率
make clean      # 清理环境
```

## Docker 部署

```bash
cd docker
./build.sh
```

或手动构建：

```bash
docker build -f docker/Dockerfile -t td-js-copilot-gpt:latest .
docker run -d -p 9003:9003 td-js-copilot-gpt:latest
```

## 相关文档

- [质差定界派单工具设计文档](docs/质差定界/质差定界派单_工具设计文档.md)
- [数据库建表脚本](docs/数据库/建表.sql)

## 许可证

内部项目
