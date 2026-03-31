import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents.example_agent import ExampleAgent, ToolAgent
from src.chains.base_chain import ExampleChain, ExtractionChain, ChatChain
from src.btree import (
    BTreeRunner,
    BTreeLoader,
    BTreeVisualizer,
    ActionRegistry,
    BTreeNode,
)
from src.utils.logger import agent_logger as logger

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation continuity")
    agent_type: str = Field(default="example", description="Agent type: example or tool")


class ChatResponse(BaseModel):
    status: bool
    message: str
    response: Optional[str] = None
    session_id: str


class ChainRequest(BaseModel):
    message: str = Field(..., description="Input message")
    chain_type: str = Field(default="example", description="Chain type: example, extraction, or chat")
    history: Optional[list] = Field(default=None, description="Conversation history for ChatChain")


class ChainResponse(BaseModel):
    status: bool
    message: str
    output: Optional[str] = None


class BTreeExecuteRequest(BaseModel):
    tree_name: str = Field(default="example_workflow", description="Behavior tree name")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input context data")


class BTreeExecuteResponse(BaseModel):
    status: str
    message: str
    context: Optional[Dict[str, Any]] = None
    execution_log: Optional[List[Dict[str, Any]]] = None


class BTreeLoadRequest(BaseModel):
    tree_json: str = Field(..., description="Behavior tree JSON string")


class BTreeInfo(BaseModel):
    name: str
    description: str


class TreeNodeInfo(BaseModel):
    name: str
    title: str
    type: str
    description: Optional[str] = None
    children: List["TreeNodeInfo"] = []


_agents: Dict[str, ExampleAgent] = {}
_btree_runners: Dict[str, BTreeRunner] = {}


def get_or_create_agent(session_id: str, agent_type: str = "example") -> ExampleAgent:
    if session_id not in _agents:
        if agent_type == "tool":
            _agents[session_id] = ToolAgent()
        else:
            _agents[session_id] = ExampleAgent()
    return _agents[session_id]


@router.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(f"[API] Chat request - session: {session_id}, message: {request.message[:50]}...")
        
        agent = get_or_create_agent(session_id, request.agent_type)
        response = await agent.arun(request.message)
        
        return ChatResponse(
            status=True,
            message="Success",
            response=response,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"[API] Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/chain/run", response_model=ChainResponse, tags=["Chain"])
async def run_chain(request: ChainRequest) -> ChainResponse:
    try:
        logger.info(f"[API] Chain request - type: {request.chain_type}, message: {request.message[:50]}...")
        
        if request.chain_type == "extraction":
            chain = ExtractionChain()
        elif request.chain_type == "chat":
            chain = ChatChain()
        else:
            chain = ExampleChain()
        
        if request.chain_type == "chat" and request.history:
            output = chain.run(question=request.message, history=request.history)
        else:
            output = chain.run(request.message)
        
        return ChainResponse(
            status=True,
            message="Success",
            output=output
        )
        
    except Exception as e:
        logger.error(f"[API] Chain error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/btree/execute", response_model=BTreeExecuteResponse, tags=["BehaviorTree"])
async def execute_btree(request: BTreeExecuteRequest) -> BTreeExecuteResponse:
    """
    Execute a behavior tree
    
    Example:
    ```json
    {
        "tree_name": "example_workflow",
        "inputs": {
            "input": "Hello",
            "fast_mode": false
        }
    }
    ```
    """
    try:
        import os
        
        logger.info(f"[API] BTree execute request - tree: {request.tree_name}")
        
        tree_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "btree", "trees", f"{request.tree_name}.json"
        )
        
        if not os.path.exists(tree_path):
            raise HTTPException(status_code=404, detail=f"Behavior tree not found: {request.tree_name}")
        
        runner = BTreeRunner()
        runner.load_btree(tree_path)
        
        result = runner.run(request.inputs)
        
        return BTreeExecuteResponse(
            status=result["status"],
            message="Behavior tree executed",
            context=result["context"],
            execution_log=result["execution_log"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] BTree execute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/btree/load", tags=["BehaviorTree"])
async def load_btree(request: BTreeLoadRequest) -> Dict[str, Any]:
    """
    Load a behavior tree from JSON string
    
    Returns the parsed tree structure
    """
    try:
        root = BTreeLoader.load_from_json(request.tree_json)
        
        return {
            "status": True,
            "message": "Behavior tree loaded",
            "tree": root.to_dict()
        }
        
    except Exception as e:
        logger.error(f"[API] BTree load error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/btree/list", response_model=List[BTreeInfo], tags=["BehaviorTree"])
async def list_btrees() -> List[BTreeInfo]:
    """
    List available behavior trees
    """
    import os
    
    trees_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "btree", "trees")
    
    if not os.path.exists(trees_dir):
        return []
    
    trees = []
    for file in os.listdir(trees_dir):
        if file.endswith(".json"):
            tree_name = file[:-5]
            trees.append(BTreeInfo(
                name=tree_name,
                description=f"Behavior tree: {tree_name}"
            ))
    
    return trees


@router.get("/api/btree/{tree_name}/visualize", tags=["BehaviorTree"])
async def visualize_btree(tree_name: str) -> Dict[str, Any]:
    """
    Get visualization data for a behavior tree
    
    Returns HTML visualization
    """
    try:
        import os
        
        tree_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "btree", "trees", f"{tree_name}.json"
        )
        
        if not os.path.exists(tree_path):
            raise HTTPException(status_code=404, detail=f"Behavior tree not found: {tree_name}")
        
        root = BTreeLoader.load_from_file(tree_path)
        
        visualizer = BTreeVisualizer(root)
        html_content = visualizer.generate_html(f"行为树: {tree_name}")
        
        return {
            "status": True,
            "html": html_content,
            "mermaid": visualizer.to_mermaid(),
            "tree_data": visualizer.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] BTree visualize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/btree/{tree_name}/structure", tags=["BehaviorTree"])
async def get_btree_structure(tree_name: str) -> Dict[str, Any]:
    """
    Get the structure of a behavior tree
    """
    try:
        import os
        
        tree_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "btree", "trees", f"{tree_name}.json"
        )
        
        if not os.path.exists(tree_path):
            raise HTTPException(status_code=404, detail=f"Behavior tree not found: {tree_name}")
        
        root = BTreeLoader.load_from_file(tree_path)
        
        return {
            "status": True,
            "tree": root.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] BTree structure error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/btree/actions", tags=["BehaviorTree"])
async def list_btree_actions() -> List[str]:
    """
    List registered behavior tree actions
    """
    return ActionRegistry.list_actions()


@router.post("/api/chat/clear", tags=["Chat"])
async def clear_history(session_id: str) -> Dict[str, Any]:
    if session_id in _agents:
        _agents[session_id].clear_history()
        del _agents[session_id]
        return {"status": True, "message": f"Session {session_id} cleared"}
    return {"status": True, "message": "Session not found"}


@router.get("/api/agents", response_model=list[BTreeInfo], tags=["Agents"])
async def list_agents() -> list[BTreeInfo]:
    return [
        BTreeInfo(name="ExampleAgent", description="A simple example agent for basic conversations"),
        BTreeInfo(name="ToolAgent", description="An agent that can use tools"),
    ]


@router.get("/api/chains", response_model=list[BTreeInfo], tags=["Chains"])
async def list_chains() -> list[BTreeInfo]:
    return [
        BTreeInfo(name="ExampleChain", description="A simple conversation chain with prompt template"),
        BTreeInfo(name="ExtractionChain", description="Extract structured information from text"),
        BTreeInfo(name="ChatChain", description="Multi-turn conversation chain with history support"),
    ]


@router.get("/api/agent/{session_id}/history", tags=["Agents"])
async def get_history(session_id: str) -> Dict[str, Any]:
    if session_id not in _agents:
        return {"status": True, "history": []}
    
    return {
        "status": True,
        "history": _agents[session_id].history
    }
