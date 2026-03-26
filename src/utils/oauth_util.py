import requests

from src.config import settings
from an_copilot.framework.logging import an_logger as logger

def get_oauth_token():
    """只是演示如何通过程序获取 OAuth2.0 访问令牌"""
    try:
        url = f"{settings.config.common_agent_config.an_oauth_base_url}/oauth/token"
        headers = {
            "Authorization": "Basic bmM6bmM=",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "username": "copilot_ces",
            "password": "copilot_ces2023",
            "grant_type": "password",
            "scope": "server",
        }

        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            response_json = response.json()
            return response_json.get("access_token")
        else:
            response.raise_for_status()
    except Exception as e:
        # 处理其他未预期异常
        logger.error(f"get_oauth_token: {str(e)}")

