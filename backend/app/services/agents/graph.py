from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from app.services.agents.state import AgentState
from app.services.agents.nodes.planner import planner_node
from app.services.agents.nodes.retriever import retriever_node
from app.services.agents.nodes.reasoner import reasoner_node
from app.services.agents.nodes.verifier import verifier_node
from app.services.agents.nodes.critic import critic_node
from app.services.agents.nodes.composer import composer_node

def route_verification(state: AgentState) -> str:
    """Conditional edge based on confidence."""
    confidence = state.get("confidence", 1.0)
    if confidence < 0.7:
        return "critic"
    return "composer"

def build_agent_graph():
    """Builds and compiles the DocsMind LangGraph."""
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("composer", composer_node)
    
    # Add Edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "retriever")
    workflow.add_edge("retriever", "reasoner")
    workflow.add_edge("reasoner", "verifier")
    
    # Conditional Routing
    workflow.add_conditional_edges(
        "verifier",
        route_verification,
        {
            "critic": "critic",
            "composer": "composer"
        }
    )
    
    # Reflection loop
    workflow.add_edge("critic", "reasoner")
    
    # Finish
    workflow.add_edge("composer", END)
    
    # Memory Checkpointer
    # In production, use AsyncPostgresSaver. For demo/rapid-arch, SQLite memory is fine.
    # conn = sqlite3.connect(":memory:", check_same_thread=False)
    # checkpointer = SqliteSaver(conn)
    
    return workflow.compile()
