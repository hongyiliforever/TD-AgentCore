import os
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class LLMConfig(BaseModel):
    openai_api_key: str = ""
    openai_api_base: str = ""
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "agent_db"


class AgentConfig(BaseModel):
    max_concurrency: int = 5
    timeout: int = 300
    retry_count: int = 3


class AppConfig(BaseModel):
    app_name: str = "LangChain Agent Framework"
    debug: bool = False
    log_level: str = "INFO"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    app: AppConfig = AppConfig()
    llm: LLMConfig = LLMConfig()
    database: DatabaseConfig = DatabaseConfig()
    agent: AgentConfig = AgentConfig()
    
    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", self.llm.openai_api_key)
    
    @property
    def openai_api_base(self) -> str:
        return os.getenv("OPENAI_API_BASE", self.llm.openai_api_base)


settings = Settings()
