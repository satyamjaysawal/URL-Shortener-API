from typing import TypedDict, List, Optional
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
import logging
from pydantic import BaseModel, Field
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class URLAnalysis(BaseModel):
    category: str = Field(description="Primary category, e.g. Technology, Finance, Education, Entertainment, Shopping, Social, News, Spam")
    safety_status: str = Field(description="'safe' if the URL content and path seem harmless, 'unsafe' if suspicious, containing phishing/spam keywords or malicious content")
    tags: List[str] = Field(description="List of 3-5 relevant keywords tags representing the domain/target content")

class AliasSuggestion(BaseModel):
    suggested_alias: str = Field(description="A single smart suggested alias of 4-6 lowercase alphanumeric characters related to the URL context")

class URLState(TypedDict):
    long_url: str
    custom_alias: Optional[str]
    category: str
    safety_status: str
    tags: List[str]
    smart_alias: Optional[str]
    error: Optional[str]

def analyze_url_node(state: URLState) -> dict:
    try:
        client = genai.Client(api_key=settings.google_api_key)
        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"Analyze this URL and determine safety and categorization: {state['long_url']}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=URLAnalysis,
            )
        )
        data = response.parsed
        return {
            "category": data.category,
            "safety_status": data.safety_status,
            "tags": data.tags,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error in analyze_url_node: {e}")
        return {
            "category": "Unknown",
            "safety_status": "safe",
            "tags": [],
            "error": str(e)
        }

def suggest_alias_node(state: URLState) -> dict:
    if state.get("custom_alias"):
        return {"smart_alias": state["custom_alias"]}
    try:
        client = genai.Client(api_key=settings.google_api_key)
        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=f"Suggest a memorable, clean 4-6 character lowercase alphanumeric alias (without space or special chars) for: {state['long_url']}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AliasSuggestion,
            )
        )
        data = response.parsed
        # Clean suggestion (alphanumeric only)
        clean_alias = "".join(c for c in data.suggested_alias if c.isalnum()).lower()
        return {"smart_alias": clean_alias or None}
    except Exception as e:
        logger.error(f"Error in suggest_alias_node: {e}")
        return {"smart_alias": None}

def governance_router(state: URLState) -> str:
    if state.get("safety_status") == "unsafe":
        return "unsafe_end"
    if not state.get("custom_alias"):
        return "suggest_alias"
    return "safe_end"

# Compile LangGraph Workflow
workflow = StateGraph(URLState)

workflow.add_node("analyze_url", analyze_url_node)
workflow.add_node("suggest_alias", suggest_alias_node)

workflow.set_entry_point("analyze_url")

workflow.add_conditional_edges(
    "analyze_url",
    governance_router,
    {
        "unsafe_end": END,
        "suggest_alias": "suggest_alias",
        "safe_end": END
    }
)

workflow.add_edge("suggest_alias", END)

agent_graph = workflow.compile()

async def run_url_agent_workflow(long_url: str, custom_alias: Optional[str] = None) -> URLState:
    """Execute the URL analysis and smart alias workflow."""
    initial_state = {
        "long_url": long_url,
        "custom_alias": custom_alias,
        "category": "Pending",
        "safety_status": "safe",
        "tags": [],
        "smart_alias": None,
        "error": None
    }
    # LangGraph run in async thread
    res = await agent_graph.ainvoke(initial_state)
    return res
