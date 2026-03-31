import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api import router
from src.utils.logger import agent_logger as logger


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app.app_name,
        description="LangChain Agent Framework - A modular agent framework built with LangChain",
        version="1.0.0",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(router)
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "app": settings.app.app_name}
    
    return app


app = create_app()


if __name__ == "__main__":
    logger.info(f"Starting {settings.app.app_name}...")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.debug,
    )
