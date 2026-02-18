"""
Workflow Definition for the Brand Guardian AI.

This module defines the Directed Acyclic Graph (DAG) that orchestrates the
video compliance audit process. It connects the nodes (functional units)
using the StateGraph primitive from LangGraph.

Architecture:
    [START] -> [index_video_node] -> [audit_content_node] -> [END]
"""

from langgraph.graph import StateGraph, END

# Import the State Schema
from backend.src.graph.state import VideoAuditState

# Import the Functional Nodes
from backend.src.graph.nodes import index_video_node

# Import the NEW Agent Nodes
from backend.src.graph.agents import (
    researcher_agent_node,
    policy_expert_node,
    chief_compliance_officer_node
)

def create_graph():
    """
    Constructs and compiles the LangGraph workflow.

    Returns:
        CompiledGraph: A runnable graph object ready for execution.
    """
    # 1. Initialize the Graph with the State Schema
    workflow = StateGraph(VideoAuditState)

    # 2. Add Nodes (The Workers)
    workflow.add_node("indexer", index_video_node)
    
    # --- NEW AGENT NODES ---
    workflow.add_node("researcher", researcher_agent_node)
    workflow.add_node("policy_expert", policy_expert_node)
    workflow.add_node("chief_officer", chief_compliance_officer_node)

    # 3. Define Edges (The Logic Flow)
    # Entry Point
    workflow.set_entry_point("indexer")

    # Flow: Indexer -> Researcher -> Policy Expert -> Chief Officer -> END
    workflow.add_edge("indexer", "researcher")
    workflow.add_edge("researcher", "policy_expert")
    workflow.add_edge("policy_expert", "chief_officer")
    workflow.add_edge("chief_officer", END)

    # 4. Compile the Graph
    app = workflow.compile()

    return app

# Expose the runnable app for import by the API or CLI
app = create_graph()