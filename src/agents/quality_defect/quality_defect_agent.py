import json
import time
from typing import ClassVar, List, Optional, Dict, Any

from an_contract.framework.agent_entity import AgentResponse
from an_copilot.framework.agent.copilot_agent import CopilotAgent, HistoryMode
from an_copilot.framework.logging import an_logger

from src.agents.quality_defect.quality_defect_runner import QualityDefectRunner
from src.config import settings


class QualityDefectAgent(CopilotAgent):
    """
    质差定界派单智能体
    - 执行质差识别检测、预警聚合、定界定位分析
    - 传参: order_id
    """
    name: str = "质差定界派单智能体"
    description: str = "自动化完成质差识别检测、预警聚合、智能定界定位分析"
    history_mode = HistoryMode.ALL.value
    skills: ClassVar[List[str]] = [
        "质差识别",
        "预警聚合",
        "定界定位",
    ]

    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            callbacks=settings.get_tracing_factory().getTracing(),
        )
        self.btree_code = settings.config.quality_defect_config.quality_defect_btree_code
        self.runner = None

    def _run(
        self,
        request_id: str,
        question: str,
        tags: Optional[List[str]] = None,
        user_agent_config: Optional[dict] = None,
        history: List[List[str]] = None,
        previous_agent_history: List[Dict[str, List[List[str]]]] = None,
        history_messages: Optional[List[Dict]] = None,
        previous_agent_history_messages: Optional[List[Dict[str, List[Dict]]]] = None,
        agent_contexts: List[str] = [],
        contexts: Optional[dict] = None,
        reasoning: Optional[bool] = False,
    ) -> AgentResponse:

        begin_time = time.time()
        order_id = None

        try:
            an_logger.info(f"QualityDefectAgent input: {question}")

            if isinstance(question, dict):
                input_json = question
            else:
                try:
                    input_json = json.loads(question)
                except (json.JSONDecodeError, TypeError):
                    input_json = {"order_id": question}

            order_id = input_json.get('order_id')
            if not order_id:
                raise ValueError("order_id is required")

            request_tag = {"request_id": request_id}
            if tags is None:
                tags = []
            tags.append(json.dumps(request_tag))

            run_context = {
                "session_id": self.session_id,
                "request_id": request_id,
                "order_id": order_id,
            }

            self.runner = QualityDefectRunner(btree_code=self.btree_code)
            self.runner.run(inputs=run_context)

            ctx = self.runner.context
            agent_output = ctx.get('agent_output') or ''

            finish_time = time.time()
            an_logger.info(f"QualityDefectAgent finished, cost: {finish_time - begin_time:.3f}s")

            return AgentResponse(
                agent_name=self.name,
                agent_input=question,
                agent_output=agent_output
            )

        except Exception as e:
            an_logger.error(f"QualityDefectAgent Exception: {e}", exc_info=True)
            return AgentResponse(
                agent_name=self.name,
                agent_input=question,
                agent_output=f"Error: {str(e)}"
            )


QualityDefectAgent.register()
