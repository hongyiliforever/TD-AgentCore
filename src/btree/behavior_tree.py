import json
import os
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.logger import agent_logger as logger


class NodeStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class NodeType(Enum):
    SEQUENCE = "sequence"
    SELECTOR = "selector"
    ACTION = "action"
    CONDITION = "condition"
    PARALLEL = "parallel"
    ROOT = "root"


class ParallelPolicy(Enum):
    SUCCESS_ON_ONE = "SuccessOnOne"
    SUCCESS_ON_ALL = "SuccessOnAll"
    FAILURE_ON_ONE = "FailureOnOne"


@dataclass
class BTreeNode:
    name: str
    title: str = ""
    description: str = ""
    node_type: NodeType = NodeType.ACTION
    children: List["BTreeNode"] = field(default_factory=list)
    func_type: str = ""
    func_name: str = ""
    func_params: Dict[str, Any] = field(default_factory=dict)
    policy: str = "SuccessOnOne"
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "type": self.node_type.value,
        }
        
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        
        if self.node_type == NodeType.ACTION:
            result["func"] = {
                "type": self.func_type,
                "schema": {
                    "name": self.func_name,
                    **self.func_params
                }
            }
        
        if self.node_type == NodeType.PARALLEL:
            result["policy"] = self.policy
        
        return result


class BTreeContext:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._results: Dict[str, Any] = {}
    
    def put(self, key: str, value: Any) -> None:
        self._data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def set_result(self, node_name: str, result: Any) -> None:
        self._results[node_name] = result
    
    def get_result(self, node_name: str) -> Any:
        return self._results.get(node_name)
    
    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)
    
    def clear(self) -> None:
        self._data.clear()
        self._results.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        return {"data": self._data.copy(), "results": self._results.copy()}


class ActionRegistry:
    _actions: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, name: str, action: Callable) -> None:
        cls._actions[name] = action
        logger.info(f"Action registered: {name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[Callable]:
        return cls._actions.get(name)
    
    @classmethod
    def list_actions(cls) -> List[str]:
        return list(cls._actions.keys())


def action(name: str):
    def decorator(func: Callable) -> Callable:
        ActionRegistry.register(name, func)
        return func
    return decorator


class BTreeLoader:
    @staticmethod
    def load_from_file(file_path: str) -> BTreeNode:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Behavior tree file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Behavior tree loaded from: {file_path}")
        return BTreeLoader._parse_node(data)
    
    @staticmethod
    def load_from_json(json_str: str) -> BTreeNode:
        data = json.loads(json_str)
        return BTreeLoader._parse_node(data)
    
    @staticmethod
    def _parse_node(data: Dict[str, Any]) -> BTreeNode:
        node_type_str = data.get("type", "action")
        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            node_type = NodeType.ACTION
        
        children = []
        for child_data in data.get("children", []):
            children.append(BTreeLoader._parse_node(child_data))
        
        func_type = ""
        func_name = ""
        func_params = {}
        
        if "func" in data:
            func_data = data["func"]
            func_type = func_data.get("type", "local")
            schema = func_data.get("schema", {})
            func_name = schema.get("name", "")
            func_params = {k: v for k, v in schema.items() if k != "name"}
        
        return BTreeNode(
            name=data.get("name", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            node_type=node_type,
            children=children,
            func_type=func_type,
            func_name=func_name,
            func_params=func_params,
            policy=data.get("policy", "SuccessOnOne"),
        )
    
    @staticmethod
    def save_to_file(root: BTreeNode, file_path: str) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(root.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Behavior tree saved to: {file_path}")


@dataclass
class ExecutionLog:
    node_name: str
    node_title: str
    node_type: str
    status: str
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: str = ""


class BTreeExecutor:
    def __init__(self, context: Optional[BTreeContext] = None):
        self.context = context or BTreeContext()
        self.execution_log: List[ExecutionLog] = []
    
    def execute(self, root: BTreeNode) -> NodeStatus:
        self.execution_log = []
        status = self._execute_node(root)
        return status
    
    def _execute_node(self, node: BTreeNode) -> NodeStatus:
        start_time = datetime.now()
        
        try:
            if node.node_type == NodeType.SEQUENCE:
                status = self._execute_sequence(node)
            elif node.node_type == NodeType.SELECTOR:
                status = self._execute_selector(node)
            elif node.node_type == NodeType.ACTION:
                status = self._execute_action(node)
            elif node.node_type == NodeType.CONDITION:
                status = self._execute_condition(node)
            elif node.node_type == NodeType.PARALLEL:
                status = self._execute_parallel(node)
            elif node.node_type == NodeType.ROOT:
                status = self._execute_root(node)
            else:
                status = NodeStatus.FAILURE
        
        except Exception as e:
            logger.error(f"Error executing node {node.name}: {e}")
            status = NodeStatus.FAILURE
            self._log_execution(node, status, error=str(e), start_time=start_time)
            return status
        
        self._log_execution(node, status, start_time=start_time)
        return status
    
    def _log_execution(
        self,
        node: BTreeNode,
        status: NodeStatus,
        output: Any = None,
        error: Optional[str] = None,
        start_time: Optional[datetime] = None
    ):
        duration = 0.0
        timestamp = ""
        if start_time:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            timestamp = start_time.isoformat()
        
        log = ExecutionLog(
            node_name=node.name,
            node_title=node.title,
            node_type=node.node_type.value,
            status=status.value,
            output=output,
            error=error,
            duration=duration,
            timestamp=timestamp,
        )
        self.execution_log.append(log)
    
    def _execute_root(self, node: BTreeNode) -> NodeStatus:
        if not node.children:
            return NodeStatus.SUCCESS
        return self._execute_node(node.children[0])
    
    def _execute_sequence(self, node: BTreeNode) -> NodeStatus:
        for child in node.children:
            status = self._execute_node(child)
            if status != NodeStatus.SUCCESS:
                return status
        return NodeStatus.SUCCESS
    
    def _execute_selector(self, node: BTreeNode) -> NodeStatus:
        for child in node.children:
            status = self._execute_node(child)
            if status == NodeStatus.SUCCESS:
                return status
        return NodeStatus.FAILURE
    
    def _execute_action(self, node: BTreeNode) -> NodeStatus:
        if not node.func_name:
            logger.warning(f"Action {node.name} has no function name, returning SUCCESS")
            return NodeStatus.SUCCESS
        
        action_func = ActionRegistry.get(node.func_name)
        if not action_func:
            logger.warning(f"Action not found: {node.func_name}, returning SUCCESS")
            return NodeStatus.SUCCESS
        
        try:
            result = action_func(self.context, **node.func_params)
            self.context.set_result(node.name, result)
            
            if isinstance(result, dict):
                status_str = result.get("status", "success")
                if status_str.lower() == "failure":
                    return NodeStatus.FAILURE
            
            return NodeStatus.SUCCESS
        except Exception as e:
            logger.error(f"Action {node.func_name} failed: {e}")
            return NodeStatus.FAILURE
    
    def _execute_condition(self, node: BTreeNode) -> NodeStatus:
        if not node.func_name:
            return NodeStatus.SUCCESS
        
        action_func = ActionRegistry.get(node.func_name)
        if not action_func:
            return NodeStatus.SUCCESS
        
        try:
            result = action_func(self.context, **node.func_params)
            if result:
                return NodeStatus.SUCCESS
            return NodeStatus.FAILURE
        except Exception as e:
            logger.error(f"Condition {node.func_name} failed: {e}")
            return NodeStatus.FAILURE
    
    def _execute_parallel(self, node: BTreeNode) -> NodeStatus:
        results = [self._execute_node(child) for child in node.children]
        
        success_count = sum(1 for r in results if r == NodeStatus.SUCCESS)
        failure_count = sum(1 for r in results if r == NodeStatus.FAILURE)
        
        policy = ParallelPolicy(node.policy)
        
        if policy == ParallelPolicy.SUCCESS_ON_ONE:
            if success_count > 0:
                return NodeStatus.SUCCESS
            return NodeStatus.FAILURE
        
        elif policy == ParallelPolicy.SUCCESS_ON_ALL:
            if success_count == len(results):
                return NodeStatus.SUCCESS
            return NodeStatus.FAILURE
        
        elif policy == ParallelPolicy.FAILURE_ON_ONE:
            if failure_count > 0:
                return NodeStatus.FAILURE
            return NodeStatus.SUCCESS
        
        return NodeStatus.SUCCESS
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        return [
            {
                "node_name": log.node_name,
                "node_title": log.node_title,
                "node_type": log.node_type,
                "status": log.status,
                "output": log.output,
                "error": log.error,
                "duration": log.duration,
                "timestamp": log.timestamp,
            }
            for log in self.execution_log
        ]


class BTreeRunner:
    def __init__(self, btree_path: Optional[str] = None):
        self.btree_path = btree_path
        self.root: Optional[BTreeNode] = None
        self.context = BTreeContext()
        self.executor = BTreeExecutor(self.context)
    
    def load_btree(self, file_path: str) -> None:
        self.root = BTreeLoader.load_from_file(file_path)
        self.btree_path = file_path
        logger.info(f"Behavior tree loaded: {file_path}")
    
    def load_btree_from_json(self, json_str: str) -> None:
        self.root = BTreeLoader.load_from_json(json_str)
        logger.info("Behavior tree loaded from JSON string")
    
    def set_context(self, data: Dict[str, Any]) -> None:
        self.context.update(data)
    
    def run(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.root:
            raise ValueError("No behavior tree loaded")
        
        if inputs:
            self.context.update(inputs)
        
        status = self.executor.execute(self.root)
        
        logger.info(f"Behavior tree execution completed with status: {status.value}")
        
        return {
            "status": status.value,
            "context": self.context.to_dict(),
            "execution_log": self.executor.get_execution_log(),
        }
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        return self.executor.get_execution_log()
