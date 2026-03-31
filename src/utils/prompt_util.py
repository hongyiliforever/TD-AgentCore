import os
import re
from typing import Dict, List, Optional

from src.utils.logger import agent_logger as logger


class PromptLoader:
    _cache: Dict[str, Dict[str, str]] = {}
    
    @classmethod
    def load_prompt(cls, filename: str, title: str, include_title: bool = True) -> Optional[str]:
        """
        Load a prompt section from a markdown file by title.
        
        Args:
            filename: The markdown file name (e.g., 'prompts.md')
            title: The first-level heading to search for
            include_title: Whether to include the title in the returned content
        
        Returns:
            The content under the specified title, or None if not found
        """
        try:
            if filename not in cls._cache:
                cls._load_file(filename)
            
            file_content = cls._cache.get(filename, {})
            content = file_content.get(title)
            
            if content is not None and include_title:
                return f"# {title}\n{content}"
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to load prompt - file: {filename}, title: {title}, error: {str(e)}")
            return None
    
    @classmethod
    def _load_file(cls, filename: str) -> None:
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompts_dir = os.path.join(current_dir, 'prompts')
            file_path = os.path.join(prompts_dir, filename)
            
            if not os.path.exists(file_path):
                logger.error(f"Prompt file not found: {file_path}")
                cls._cache[filename] = {}
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            sections = cls._parse_sections(content)
            cls._cache[filename] = sections
            
            logger.info(f"Loaded prompt file: {filename}, contains {len(sections)} sections")
            
        except Exception as e:
            logger.error(f"Failed to load prompt file - file: {filename}, error: {str(e)}")
            cls._cache[filename] = {}
    
    @classmethod
    def _parse_sections(cls, content: str) -> Dict[str, str]:
        sections = {}
        parts = re.split(r'^(# .+)$', content, flags=re.MULTILINE)
        
        current_title = None
        current_content = ""
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if part.startswith('# '):
                if current_title is not None:
                    sections[current_title] = current_content.strip()
                current_title = part[2:].strip()
                current_content = ""
            else:
                if current_content:
                    current_content += "\n" + part
                else:
                    current_content = part
        
        if current_title is not None:
            sections[current_title] = current_content.strip()
        
        return sections
    
    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
        logger.info("Prompt cache cleared")
    
    @classmethod
    def get_available_titles(cls, filename: str) -> List[str]:
        if filename not in cls._cache:
            cls._load_file(filename)
        
        file_content = cls._cache.get(filename, {})
        return list(file_content.keys())


get_markdown_content_by_title = PromptLoader.load_prompt
