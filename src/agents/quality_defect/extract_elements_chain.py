import time
import json
import re
from typing import Any, Dict, List, Optional

from an_copilot.framework.chain.copilot_chain import CopilotChain, LLmGeneration
from an_copilot.framework.logging import an_logger
from langchain_core.callbacks import CallbackManagerForChainRun
from langchain_core.prompts import PromptTemplate

from src.utils.knowledge_util import get_markdown_content_by_title


class ExtractElementsChain(CopilotChain):
    prompt_title: str = "智能回单要素提取"
    prompt_file: str = "reply_prompt.md"

    def get_name(self) -> str:
        return "要素提取"

    def description(self) -> str:
        return "提取四大核心要素"

    @property
    def input_keys(self) -> List[str]:
        return ["question", "history"]

    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]

    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, str]:
        try:
            begin_time = time.time()
            question = inputs.get("question", "")
            an_logger.info(f"[ExtractElementsChain] 开始执行: {self.prompt_title}")

            prompt_template = get_markdown_content_by_title(self.prompt_file, self.prompt_title)
            if not prompt_template:
                an_logger.error(f"未找到 Prompt: {self.prompt_file} - {self.prompt_title}")
                return self.response_wrapper(LLmGeneration(content=json.dumps(self._default_result(), ensure_ascii=False)))

            prompt = PromptTemplate.from_template(prompt_template)
            prompt_value = prompt.format_prompt(input=question)

            response = self.llm_stream(
                messages=[prompt_value.to_messages()], run_manager=run_manager
            )

            result = self._parse_response(response.content)

            end_time = time.time()
            an_logger.info(f"[ExtractElementsChain] 完成, 耗时: {end_time - begin_time:.3f}s")

            return self.response_wrapper(LLmGeneration(content=json.dumps(result, ensure_ascii=False)))
        except Exception as e:
            an_logger.error(f"[ExtractElementsChain] 异常: {e}", exc_info=True)
            return self.response_wrapper(LLmGeneration(content=json.dumps(self._default_result(), ensure_ascii=False)))

    def _parse_response(self, content: str) -> dict:
        try:
            cleaned = content.strip()
            
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:].rsplit('```', 1)[0].strip()
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:].rsplit('```', 1)[0].strip()
            
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                return json.loads(json_match.group())
            
            return self._default_result()
        except Exception as e:
            an_logger.error(f"[ExtractElementsChain] JSON解析失败: {e}")
            return self._default_result()

    def _default_result(self) -> dict:
        return {
            "extracted_complaint_time": {"date": "", "period": "未提及", "source": "order"},
            "complaint_location": {"longitude": 0.0, "latitude": 0.0, "description": "", "source": "original"},
            "problem_type": {"category": "其他", "description": "", "other_reason_remark": "", "confidence": 0.0},
            "surrounding_situation": {"mentioned": False, "content": "未提及"}
        }
