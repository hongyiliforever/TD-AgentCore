from typing import Any, Dict

from src.btree.behavior_tree import BTreeContext, action
from src.utils.logger import agent_logger as logger


@action("check_input")
def action_check_input(context: BTreeContext, **kwargs) -> Dict[str, Any]:
    has_input = context.get("input") is not None
    logger.info(f"[BTree] 检查输入: {has_input}")
    
    if has_input:
        return {"status": "success", "message": "输入有效"}
    return {"status": "failure", "message": "无输入"}


@action("initialize")
def action_initialize(context: BTreeContext, **kwargs) -> Dict[str, Any]:
    context.put("initialized", True)
    context.put("step", "initialized")
    logger.info("[BTree] 初始化完成")
    return {"status": "success", "message": "初始化完成"}


@action("can_fast_process")
def action_can_fast_process(context: BTreeContext, **kwargs) -> Dict[str, Any]:
    fast_mode = context.get("fast_mode", False)
    logger.info(f"[BTree] 检查快速模式: {fast_mode}")
    
    if fast_mode:
        return {"status": "success", "message": "可以快速处理"}
    return {"status": "failure", "message": "需要标准处理"}


@action("fast_process")
def action_fast_process(context: BTreeContext, **kwargs) -> Dict[str, Any]:
    context.put("process_type", "fast")
    context.put("step", "fast_processed")
    logger.info("[BTree] 快速处理完成")
    return {"status": "success", "message": "快速处理完成"}


@action("standard_process")
def action_standard_process(context: BTreeContext, **kwargs) -> Dict[str, Any]:
    context.put("process_type", "standard")
    context.put("step", "standard_processed")
    logger.info("[BTree] 标准处理完成")
    return {"status": "success", "message": "标准处理完成"}


@action("output_result")
def action_output_result(context: BTreeContext, **kwargs) -> Dict[str, Any]:
    process_type = context.get("process_type", "unknown")
    result = f"处理完成，使用方式: {process_type}"
    context.put("final_result", result)
    logger.info(f"[BTree] {result}")
    return {"status": "success", "message": result}


@action("log_message")
def action_log_message(context: BTreeContext, message: str = "", **kwargs) -> Dict[str, Any]:
    logger.info(f"[BTree] {message}")
    return {"status": "success", "message": message}


@action("set_context")
def action_set_context(context: BTreeContext, key: str = "", value: Any = None, **kwargs) -> Dict[str, Any]:
    if key:
        context.put(key, value)
        logger.info(f"[BTree] 设置上下文: {key} = {value}")
    return {"status": "success", "message": f"设置上下文: {key} = {value}"}


@action("call_agent")
def action_call_agent(context: BTreeContext, agent_name: str = "", input_key: str = "input", **kwargs) -> Dict[str, Any]:
    from src.agents import ExampleAgent
    
    if not agent_name:
        return {"status": "failure", "message": "未指定智能体名称"}
    
    input_text = context.get(input_key, "")
    
    agent = ExampleAgent()
    result = agent.run(input_text)
    
    context.put("agent_result", result)
    logger.info(f"[BTree] 调用智能体 {agent_name} 完成")
    return {"status": "success", "message": result}


@action("call_chain")
def action_call_chain(context: BTreeContext, chain_type: str = "example", input_key: str = "input", **kwargs) -> Dict[str, Any]:
    from src.chains import ExampleChain, ExtractionChain
    
    input_text = context.get(input_key, "")
    
    if chain_type == "extraction":
        chain = ExtractionChain()
    else:
        chain = ExampleChain()
    
    result = chain.run(input_text)
    context.put("chain_result", result)
    logger.info(f"[BTree] 调用链 {chain_type} 完成")
    return {"status": "success", "message": result}
