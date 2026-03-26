import os
from typing import Dict, Any, Optional
from an_copilot.framework.logging import an_logger
from an_copilot.framework.config.common_settings import CommonConfig, CommonSettings
from pydantic import BaseModel


def prepare_environment(config_json: Dict):
    if "common_agent_config" not in config_json:
        config_json["common_agent_config"] = {}

    if "quality_defect_config" not in config_json:
        config_json["quality_defect_config"] = {}
    if "quality_defect_btree_code" not in config_json["quality_defect_config"]:
        config_json["quality_defect_config"]["quality_defect_btree_code"] = ""
    if os.environ.get("quality_defect_btree_code"):
        config_json["quality_defect_config"]["quality_defect_btree_code"] = os.environ.get("quality_defect_btree_code")


class CommonAgentConfig(BaseModel):
    tickets_detail_url: str = ""
    tickets_system_type: str = ""


class QualityDefectConfig(BaseModel):
    quality_defect_btree_code: str = ""
    quality_defect_detect_url: str = ""
    quality_defect_alert_url: str = ""
    quality_defect_localization_url: str = ""


class AgentRuntimeConfig(BaseModel):
    max_concurrency: int = 5
    db_pool_recycle: int = 3600


class Config(CommonConfig):
    common_agent_config: CommonAgentConfig = CommonAgentConfig()
    quality_defect_config: QualityDefectConfig = QualityDefectConfig()
    agent_runtime_config: Optional[AgentRuntimeConfig] = AgentRuntimeConfig()


class Settings(CommonSettings):
    def __init__(self):
        super().__init__(
            custom_config_path=os.path.join(os.path.dirname(__file__), "config.json"),
            custom_prepare_environment=prepare_environment,
            custom_config_cls=Config,
            prompts_path=os.path.join(os.path.dirname(__file__), "../prompts"),
        )
