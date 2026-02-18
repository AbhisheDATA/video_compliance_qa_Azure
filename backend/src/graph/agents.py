import json
import os
import logging
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

# Import Telemetry Helpers
from backend.src.api.telemetry import (
    track_token_usage, 
    track_audit_decision, 
    start_agent_timer, 
    end_agent_timer
)

# Import State Schema
from backend.src.graph.state import VideoAuditState

logger = logging.getLogger("agent-council")

# --- INITIALIZE COMMON MODELS ---
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.0,
        api_key=os.getenv("GOOGLE_API_KEY")
    )

def get_vector_store():
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment="embedding-large",
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )
    return AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        embedding_function=embeddings.embed_query
    )

# --- AGENT 1: THE RESEARCHER 🕵️ ---
def researcher_agent_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Role: Analyzes raw video data (Transcript/OCR) to extract factual claims and context.
    Does NOT judge compliance, just gathers facts.
    """
    logger.info("--- [Agent: Researcher] Extracting key facts ---")
    start_time = start_agent_timer("Researcher")
    
    transcript = state.get("transcript", "")
    ocr = state.get("ocr_text", [])
    
    if not transcript:
        end_agent_timer("Researcher", start_time)
        return {"research_notes": "Error: No transcript available for analysis."}

    llm = get_llm()
    
    system_prompt = """
    You are a Forensic Video Researcher. 
    Your job is to extract factual claims, guarantees, and on-screen disclaimers from the provided transcript and OCR text.
    
    Output a structured summary containing:
    1. Key Claims made by the speaker.
    2. Any absolute guarantees (e.g., "100% safe").
    3. Visible text/disclaimers from OCR.
    4. Tone analysis (e.g., "Urgent", "Informational").
    
    Be objective. Do not judge compliance yet.
    """
    
    user_message = f"""
    TRANSCRIPT: {transcript[:10000]} ... (truncated if too long)
    OCR TEXT: {ocr}
    """
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])
    
    # Telemetry: Track Tokens and Latency
    if hasattr(response, "usage_metadata"):
        track_token_usage("Researcher", response.usage_metadata.get("total_tokens", 0))
    end_agent_timer("Researcher", start_time)
    
    return {"research_notes": response.content}


# --- AGENT 2: THE POLICY EXPERT ⚖️ ---
def policy_expert_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Role: Retrieves relevant rules and interprets them based on the Researcher's notes.
    """
    logger.info("--- [Agent: Policy Expert] Interpreting Rules ---")
    start_time = start_agent_timer("PolicyExpert")
    
    research_notes = state.get("research_notes", "")
    
    # 1. RAG Retrieval based on research notes
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(research_notes, k=3)
    retrieved_rules = "\n\n".join([doc.page_content for doc in docs])
    
    # 2. Interpretation
    llm = get_llm()
    
    system_prompt = f"""
    You are a Senior Policy Legal Expert.
    
    RELEVANT LAWS/RULES:
    {retrieved_rules}
    
    INSTRUCTIONS:
    Review the Researcher's Notes below. 
    For each claim identified, interpret how the retrieved rules apply.
    Cite specific rules for every interpretation.
    """
    
    user_message = f"RESEARCHER NOTES:\n{research_notes}"
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])
    
    # Telemetry: Track Tokens and Latency
    if hasattr(response, "usage_metadata"):
        track_token_usage("PolicyExpert", response.usage_metadata.get("total_tokens", 0))
    end_agent_timer("PolicyExpert", start_time)
    
    return {"policy_analysis": response.content}


# --- AGENT 3: THE CHIEF COMPLIANCE OFFICER 👩‍⚖️ ---
def chief_compliance_officer_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Role: Makes the final PASS/FAIL decision based on previous agents' work.
    Generates the final JSON report.
    """
    logger.info("--- [Agent: Chief Compliance Officer] Finalizing Verdict ---")
    start_time = start_agent_timer("ChiefComplianceOfficer")
    
    research_notes = state.get("research_notes", "")
    policy_analysis = state.get("policy_analysis", "")
    
    llm = get_llm()
    
    system_prompt = """
    You are the Chief Compliance Officer.
    
    Review the evidence from your team (Researcher and Policy Expert).
    Make a final binding decision.
    
    Output strictly JSON:
    {
        "compliance_results": [
            {"category": "...", "severity": "...", "description": "..."}
        ],
        "status": "PASS" | "FAIL",
        "final_report": "Executive summary of the decision..."
    }
    """
    
    user_message = f"""
    EVIDENCE (Researcher): {research_notes}
    LEGAL OPINION (Policy Expert): {policy_analysis}
    """
    
    # Ensure JSON output
    response = llm.invoke([
        SystemMessage(content=system_prompt), 
        HumanMessage(content=user_message)
    ])
    
    # Telemetry: Track Tokens
    if hasattr(response, "usage_metadata"):
        track_token_usage("ChiefComplianceOfficer", response.usage_metadata.get("total_tokens", 0))
    
    # Simple JSON cleaning (same as before)
    import re
    content = response.content
    if "```" in content:
        content = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL).group(1)
            
    try:
        final_data = json.loads(content.strip())
        status = final_data.get("status", "FAIL")
        
        # Telemetry: Track Verdict
        track_audit_decision(status)
        end_agent_timer("ChiefComplianceOfficer", start_time)
        
        return {
            "compliance_results": final_data.get("compliance_results", []),
            "final_status": status,
            "final_report": final_data.get("final_report", "Report generated.")
        }
    except Exception as e:
        logger.error(f"JSON Parse Error: {e}")
        end_agent_timer("ChiefComplianceOfficer", start_time)
        return {
            "final_status": "FAIL",
            "errors": ["Failed to parse CCO decision."]
        }
