import json
from an_copilot.framework.utils.btree import BTree, BtreeContext, BtreeRegistry
from an_copilot.framework.logging import an_logger
from an_copilot.framework.utils.httpclient import HttpClient
from src.config import settings


class QualityDefectRunner:
    """
    质差定界派单行为树运行器
    """

    def __init__(self, btree_code: str):
        self.btree_code = btree_code
        self.http_client = HttpClient(base_url=settings.config.ces.uri)
        self.context = None

    def run(self, inputs: dict = None):
        """执行行为树"""
        self._init_context(inputs)

        btree_json = self._fetch_btree_config(self.btree_code)
        an_logger.info(f"QualityDefectRunner {self.btree_code} loaded.")

        btree = BTree.from_config(
            btree_json,
            BtreeRegistry.get_nodes(),
            context=self.context,
        )
        response = btree.run(show_status=True)
        an_logger.info(f"QualityDefectRunner execution finished.")

        self._log_results(response)

    def _init_context(self, inputs: dict):
        """初始化上下文"""
        self.context = BtreeContext()
        if inputs:
            for k, v in inputs.items():
                self.context.put(k, v)

    def _fetch_btree_config(self, code: str) -> dict:
        """获取行为树配置"""
        headers = {"Content-Type": "application/json", "Accept": "application/json", "from": "Y"}
        endpoint = f"/workflow/getNodesJson?code={code}&version=1.0.0"
        response = self.http_client.get(endpoint=endpoint, headers=headers)
        data = response.json()["data"]
        return json.loads(data) if isinstance(data, str) else data

    def _log_results(self, response):
        """记录执行结果"""
        for node in response.get_nodes():
            if node.type == "action" and node.status.name != "INVALID":
                an_logger.info(f"[{node.name}] status={node.status.name}, duration={node.duration:.3f}s")
