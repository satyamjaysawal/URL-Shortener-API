from typing import TypedDict, List, Optional, AsyncIterator, Any, Dict, NotRequired
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
import logging
from pydantic import BaseModel, Field
from app.config import get_settings
import time

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
    gemini_api_key: NotRequired[Optional[str]]

def _resolve_api_key(state: URLState) -> Optional[str]:
    """Prefer per-request user key; fall back to server .env key."""
    user_key = (state.get("gemini_api_key") or "").strip()
    if user_key:
        return user_key
    return settings.google_api_key


def analyze_url_node(state: URLState) -> dict:
    try:
        client = genai.Client(api_key=_resolve_api_key(state))
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
        client = genai.Client(api_key=_resolve_api_key(state))
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

# LangGraph DAG metadata exposed to the UI
GRAPH_METADATA = {
    "nodes": [
        {"id": "start", "label": "Entry", "type": "entry", "description": "Initialize agent state"},
        {"id": "analyze_url", "label": "Analyze URL", "type": "agent", "description": "Gemini safety scan & categorization"},
        {"id": "governance", "label": "Governance Gate", "type": "gate", "description": "Policy router — safety & compliance check"},
        {"id": "suggest_alias", "label": "Suggest Alias", "type": "agent", "description": "AI smart alias generation", "optional": True},
        {"id": "end", "label": "Complete", "type": "exit", "description": "Workflow finished"},
    ],
    "edges": [
        {"from": "start", "to": "analyze_url"},
        {"from": "analyze_url", "to": "governance"},
        {"from": "governance", "to": "suggest_alias", "label": "safe, no alias"},
        {"from": "governance", "to": "end", "label": "unsafe / has alias"},
        {"from": "suggest_alias", "to": "end"},
    ],
}

ROUTE_MESSAGES = {
    "unsafe_end": "URL flagged unsafe — blocking workflow",
    "suggest_alias": "Safe URL — routing to alias suggestion agent",
    "safe_end": "Safe URL with custom alias — skipping alias agent",
}


def _initial_state(
    long_url: str,
    custom_alias: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> URLState:
    state: URLState = {
        "long_url": long_url,
        "custom_alias": custom_alias,
        "category": "Pending",
        "safety_status": "safe",
        "tags": [],
        "smart_alias": None,
        "error": None,
    }
    if gemini_api_key and gemini_api_key.strip():
        state["gemini_api_key"] = gemini_api_key.strip()
    return state


def _api_key_source(gemini_api_key: Optional[str]) -> str:
    return "user" if gemini_api_key and gemini_api_key.strip() else "server"


def _serialize_output(data: dict) -> dict:
    """Make node output JSON-serializable for SSE."""
    return {k: v for k, v in data.items() if v is not None}


def _build_analysis_result(state: URLState, long_url: str) -> dict:
    safety = state.get("safety_status", "safe")
    return {
        "long_url": long_url,
        "category": state.get("category", "Unknown"),
        "safety_status": safety,
        "tags": state.get("tags", []),
        "suggested_alias": state.get("smart_alias"),
        "safe_to_shorten": safety != "unsafe",
        "model": settings.gemini_flash_model,
    }


async def stream_url_agent_workflow(
    long_url: str,
    custom_alias: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream LangGraph agent execution as SSE-friendly events.
    Uses agent_graph.astream(stream_mode='updates') for real node-by-node updates.
    """
    initial_state = _initial_state(long_url, custom_alias, gemini_api_key)
    final_state: dict = dict(initial_state)
    workflow_started = time.perf_counter()

    yield {
        "event": "workflow_start",
        "graph": GRAPH_METADATA,
        "input": {"long_url": long_url, "custom_alias": custom_alias},
        "api_key_source": _api_key_source(gemini_api_key),
        "message": "LangGraph agent workflow started",
    }

    yield {"event": "node_start", "node": "start", "message": "Initializing agent state…"}
    yield {"event": "node_complete", "node": "start", "data": {"status": "ready"}, "duration_ms": 0}

    yield {
        "event": "node_start",
        "node": "analyze_url",
        "message": f"Calling {settings.gemini_flash_model} for safety & categorization…",
    }

    suggest_alias_started = False
    governance_emitted = False
    end_emitted = False
    node_timers: Dict[str, float] = {"analyze_url": time.perf_counter()}

    async for chunk in agent_graph.astream(initial_state, stream_mode="updates"):
        for node_name, update in chunk.items():
            if node_name == "suggest_alias" and not suggest_alias_started:
                suggest_alias_started = True
                node_timers["suggest_alias"] = time.perf_counter()
                yield {
                    "event": "node_start",
                    "node": "suggest_alias",
                    "message": f"Calling {settings.gemini_flash_model} for smart alias…",
                }

            started = node_timers.get(node_name, time.perf_counter())
            final_state.update(update)
            yield {
                "event": "node_complete",
                "node": node_name,
                "data": _serialize_output(update),
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            }

            if node_name == "analyze_url" and not governance_emitted:
                governance_emitted = True
                yield {
                    "event": "node_start",
                    "node": "governance",
                    "message": "Evaluating governance policy router…",
                }
                route = governance_router(final_state)
                yield {
                    "event": "governance_decision",
                    "node": "governance",
                    "route": route,
                    "message": ROUTE_MESSAGES.get(route, route),
                    "data": {
                        "safety_status": final_state.get("safety_status"),
                        "category": final_state.get("category"),
                    },
                }
                yield {
                    "event": "node_complete",
                    "node": "governance",
                    "data": {"route": route, "decision": ROUTE_MESSAGES.get(route)},
                }

                if route == "unsafe_end":
                    yield {
                        "event": "node_skipped",
                        "node": "suggest_alias",
                        "reason": "Blocked by governance — unsafe URL",
                    }
                    yield {"event": "node_start", "node": "end", "message": "Workflow blocked by governance"}
                    yield {
                        "event": "node_complete",
                        "node": "end",
                        "data": {"status": "blocked", "reason": "unsafe"},
                    }
                    end_emitted = True
                elif route == "safe_end":
                    yield {
                        "event": "node_skipped",
                        "node": "suggest_alias",
                        "reason": "Custom alias provided — alias agent skipped",
                    }

    if not end_emitted:
        yield {"event": "node_start", "node": "end", "message": "Workflow completed successfully"}
        yield {
            "event": "node_complete",
            "node": "end",
            "data": {"status": "success", "smart_alias": final_state.get("smart_alias")},
        }

    total_ms = round((time.perf_counter() - workflow_started) * 1000, 1)
    yield {
        "event": "workflow_complete",
        "result": _build_analysis_result(final_state, long_url),
        "duration_ms": total_ms,
        "message": "LangGraph workflow finished",
    }


async def run_url_agent_workflow(
    long_url: str,
    custom_alias: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> URLState:
    """Execute the URL analysis and smart alias workflow."""
    res = await agent_graph.ainvoke(_initial_state(long_url, custom_alias, gemini_api_key))
    return res
