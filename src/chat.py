from an_copilot.framework.bootstrap_tester import tester_start
from src.agents import *  # noqa: F403 F401 不能删除
from src.config import settings


tester_start(settings=settings)
