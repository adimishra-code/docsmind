from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    The central state for the DocsMind LangGraph orchestration.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    user_id: str
    
    # Execution Plan
    plan: str
    
    # Retrieval
    document_ids: list[str]
    retrieved_chunks: list[dict]
    
    # Tool Execution
    tool_calls: list[dict]
    tool_outputs: list[dict]
    
    # Verification & Criticism
    confidence: float
    citations: list[dict]
    verification_feedback: str
    # Number of critic->reasoner revision cycles taken. Bounded to prevent an
    # unbounded loop when confidence never crosses the acceptance threshold.
    revision_count: int
    
    # End state
    final_response: str
