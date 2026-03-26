from an_copilot.framework import bootstrap

from src.api import order_tool_api
from src.api import wo_agent_api
from src.api import wo_call_api
from src.api import voice_format_api
from src.api import smart_reply_api
from src.api import quality_defect_api

bootstrap.include_router(order_tool_api.router)
bootstrap.include_router(wo_agent_api.router)
bootstrap.include_router(wo_call_api.router)
bootstrap.include_router(voice_format_api.router)
bootstrap.include_router(smart_reply_api.router)
bootstrap.include_router(quality_defect_api.router)


