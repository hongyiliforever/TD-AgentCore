import json
import os
from typing import List, Dict, Optional
from an_copilot.framework.logging import an_logger as logger
import requests
from json.decoder import JSONDecodeError
from src.config import settings
from src.utils.oauth_util import get_oauth_token
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def similarity_search(text: str, repository_alias: List[str], top_k: int = 1) -> List[str]:
    access_token = get_oauth_token()  # 如果通过CES访问，那么不需要此步骤
    url = f"{settings.config.common_agent_config.an_copilot_knowledge_base_url}/v1/api/knowledge/repository/vectors/similarity_search"
    headers = {
        "Content-Type": "application/json",
         "Authorization": f"Bearer {access_token}",  # 如果通过CES访问，那么不需要此步骤
    }
    data = {
        "text": text,
        "top_k": top_k,
        "embeder_name": "HuggingFace",
        "repository_alias": repository_alias,
    }
    try:

        response = requests.post(url, headers=headers, data=json.dumps(data))
        # 解析JSON响应
        try:
            response_json = response.json()
            logger.info(f"知识库similarity_search {text}: {response_json}")
        except JSONDecodeError as e:
            logger.error(f"similarity_search - {text}  失败: {str(e)}，响应内容: {response.text}")

        if response.status_code == 200:
            segment_contents = []
            rerank_segments = response.json()["data"]["segments"]
            for segment in rerank_segments:
                segment_contents.append(segment["segment_content"])
            return segment_contents
        else:
            response.raise_for_status()  # 抛出异常以处理错误响应

    except Exception as e:
        logger.error(f"知识库similarity_search {text}: {str(e)}")


# 全局缓存字典，用于存储已加载的markdown文件内容
_markdown_cache: Dict[str, Dict[str, str]] = {}


def get_markdown_content_by_title(filename: str, title: str, include_title: bool = True) -> Optional[str]:
    """
    根据一级标题从markdown文件中获取内容
    
    Args:
        filename: markdown文件名（如：'order_rules_prompt.md'）
        title: 一级标题名称（如：'基础信息'）
        include_title: 是否在返回内容中包含一级标题，默认为True
    
    Returns:
        对应标题下的内容，如果未找到则返回None
    """
    try:
        # 检查缓存中是否已加载该文件
        if filename not in _markdown_cache:
            _load_markdown_file(filename)
        
        # 从缓存中获取指定标题的内容
        file_content = _markdown_cache.get(filename, {})
        content = file_content.get(title)
        
        if content is not None and include_title:
            # 在内容前添加一级标题
            return f"# {title}\n{content}"
        
        return content
        
    except Exception as e:
        logger.error(f"获取markdown内容失败 - 文件: {filename}, 标题: {title}, 错误: {str(e)}")
        return None


def _load_markdown_file(filename: str) -> None:
    """
    加载markdown文件并按一级标题分割内容到缓存中
    
    Args:
        filename: markdown文件名
    """
    try:
        # 构建文件路径，支持相对路径和docker部署
        # 获取当前文件所在目录的父目录的父目录（src目录）
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        knowledges_dir = os.path.join(current_dir, 'knowledges')
        file_path = os.path.join(knowledges_dir, filename )
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"markdown文件不存在: {file_path}")
            _markdown_cache[filename] = {}
            return
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按一级标题分割内容
        sections = _parse_markdown_sections(content)
        
        # 缓存分割后的内容
        _markdown_cache[filename] = sections
        
        logger.info(f"成功加载markdown文件: {filename}, 包含 {len(sections)} 个一级标题")
        
    except Exception as e:
        logger.error(f"加载markdown文件失败 - 文件: {filename}, 错误: {str(e)}")
        _markdown_cache[filename] = {}


def _parse_markdown_sections(content: str) -> Dict[str, str]:
    """
    解析markdown内容，按一级标题分割
    
    Args:
        content: markdown文件的完整内容
    
    Returns:
        字典，键为一级标题，值为该标题下的内容
    """
    sections = {}
    
    # 使用正则表达式匹配一级标题（# 标题）
    # 分割内容，保留分隔符
    parts = re.split(r'^(# .+)$', content, flags=re.MULTILINE)
    
    current_title = None
    current_content = ""
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # 检查是否是一级标题
        if part.startswith('# '):
            # 保存上一个标题的内容
            if current_title is not None:
                sections[current_title] = current_content.strip()
            
            # 开始新的标题
            current_title = part[2:].strip()  # 去掉 "# " 前缀
            current_content = ""
        else:
            # 累积当前标题下的内容
            if current_content:
                current_content += "\n" + part
            else:
                current_content = part
    
    # 保存最后一个标题的内容
    if current_title is not None:
        sections[current_title] = current_content.strip()
    
    return sections


def clear_markdown_cache() -> None:
    """
    清空markdown文件缓存
    """
    global _markdown_cache
    _markdown_cache.clear()
    logger.info("已清空markdown文件缓存")


def get_available_titles(filename: str) -> List[str]:
    """
    获取指定markdown文件中所有可用的一级标题
    
    Args:
        filename: markdown文件名
    
    Returns:
        一级标题列表
    """
    try:
        # 确保文件已加载
        if filename not in _markdown_cache:
            _load_markdown_file(filename)
        
        file_content = _markdown_cache.get(filename, {})
        return list(file_content.keys())
        
    except Exception as e:
        logger.error(f"获取可用标题失败 - 文件: {filename}, 错误: {str(e)}")
        return []


if __name__ == '__main__':

    print(get_markdown_content_by_title('cpl_msg_prompt.md', '任务执行'))
