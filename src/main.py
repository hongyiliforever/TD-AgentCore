
from an_copilot.framework.bootstrap import bootstrap_start
from src.config import settings
import src.api  # noqa: F401

if __name__ == "__main__":
    # 创建定时任务线程
    bootstrap_start(project_name="wo-copilot-gpt", settings=settings)


