import asyncio
from src.config import settings
from src.agents.example_agent import ExampleAgent
from src.utils.logger import agent_logger as logger


async def main():
    logger.info(f"Starting {settings.app.app_name} chat test...")
    
    agent = ExampleAgent()
    
    test_input = "请帮我分析一下今天的天气情况"
    
    logger.info(f"Input: {test_input}")
    
    result = await agent.arun(test_input)
    
    logger.info(f"Output: {result}")
    
    print("\n" + "=" * 50)
    print("Agent Response:")
    print("=" * 50)
    print(result)
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
