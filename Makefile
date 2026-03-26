# ==========================================
# Windows Git Bash 专用配置 (Anaconda源)
# ==========================================

# 1. 定义配置
VENV := .venv
# 你的Python正确路径
BASE_PYTHON := C:/Users/AI/PycharmProjects/td-copilot-gpt/.venv/Scripts/python.exe

# 定义虚拟环境内部的工具路径
PYTHON := $(VENV)/Scripts/python
PIP := $(VENV)/Scripts/pip
STREAMLIT := $(VENV)/Scripts/streamlit
PFLAKE8 := $(VENV)/Scripts/pflake8
PYTEST := $(VENV)/Scripts/pytest

.PHONY: init run chat fmt lint coverage clean

# 2. 初始化环境
init:
	@echo "========================================"
	@echo "步骤 1/3: 清理旧环境..."
	@echo "========================================"
	rm -rf $(VENV)

	@echo "========================================"
	@echo "步骤 2/3: 使用指定 Python 创建新环境..."
	@echo "源路径: $(BASE_PYTHON)"
	@echo "========================================"
	"$(BASE_PYTHON)" -m venv $(VENV)

	@echo "========================================"
	@echo "步骤 3/3: 安装依赖 (使用 .venv 内部 pip)..."
	@echo "========================================"
	# 升级 pip ✅ 修复正确
	$(PYTHON) -m pip install --upgrade pip
	# 卸载冲突包 (忽略错误)
	$(PIP) uninstall -y an-copilot pydantic || true
	# 安装项目依赖
	$(PIP) install . '.[lint]' '.[test]' '.[package]' \
      --trusted-host 10.1.207.194 --default-timeout=600 \
      --extra-index-url http://10.1.207.194:8099/nexus/repository/pypi-group/simple/ \
      -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 3. 运行服务
run:
	export PYTHONPATH=$${PYTHONPATH}:. && $(PYTHON) src/main.py -H 0.0.0.0 -P 5000

# 4. 运行 Streamlit
chat:
	export PYTHONPATH=$${PYTHONPATH}:. && $(STREAMLIT) run src/chat.py --server.address=127.0.0.1 --server.port=5000

# 5. 代码格式化
fmt:
	$(PYTHON) -m black ./src ./tests
	$(PYTHON) -m isort --profile black ./src ./tests
	@$(MAKE) lint

# 6. 代码检查
lint:
	$(PFLAKE8) ./src ./tests

# 7. 测试覆盖率
coverage: lint
	$(PYTEST) --cov=src tests

# 清理
clean:
	rm -rf $(VENV)