"""
LangGraph Agent Module for CMS AI Assistant.
Orchestrates Natural Language Understanding, Vector Database Embeddings Retrieval (RAG),
Read-Only SQL Database Querying, and Visualization Synthesis using LangGraph StateGraph.
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from aiml.chatbot.intent_parser import (
    parse_intent_and_entities,
    INTENT_GREETING, INTENT_HELP, INTENT_DYNAMIC_CHART, INTENT_REPORT_GEN,
    INTENT_CATEGORY_COMPARISON, INTENT_LOW_STOCK_DEFICIENCY, INTENT_SALES_ISSUANCE,
    INTENT_PRODUCT_INFO, INTENT_INVENTORY_SUMMARY, INTENT_UNIT_INFO, INTENT_USER_INFO,
    INTENT_AUTHORIZATION_INFO, INTENT_RESERVE_STOCK
)
from aiml.chatbot.vector_store import get_vector_db
from aiml.chatbot.sql_chain import LangChainSQLChain
from aiml.chatbot.database_tool import DatabaseTool
from aiml.chatbot.tools import ChatTool, ChartTool, ReportTool, SummaryTool
from aiml.chatbot.prompt import CMS_SYSTEM_PROMPT, build_ollama_prompt

STANDARD_DB_INTENTS = {
    "PRODUCT_INFO", "INVENTORY_SUMMARY", "USER_INFO", "CATEGORY_COMPARISON",
    "LOW_STOCK_DEFICIENCY", "SALES_ISSUANCE", "AUTHORIZATION_INFO",
    "RESERVE_STOCK", "REPORT_GEN", "UNIT_INFO", "DOU_INFO"
}

KNOWLEDGE_KEYWORDS = [
    "what is", "what are", "difference", "policy", "explain", "guide", "cat-i", "cat-ii",
    "category 1", "category 2", "meaning", "definition", "how does", "how is", "workflow",
    "rule", "guideline", "donut chart", "au split", "accounting unit", "productive analysis",
    "deficiency share", "readiness color", "scme role", "ord role", "division role"
]


class CMSGraphState(TypedDict, total=False):
    """LangGraph State representation for the CMS AI Assistant workflow."""
    user_query: str
    session_id: str
    user_role: str
    intent: str
    entities: Dict[str, Any]
    memory_context: Optional[Dict[str, Any]]
    route: str  # "conversational", "vector_rag", "sql_db", "hybrid", "chart"
    retrieved_docs: List[Dict[str, Any]]
    rag_context: str
    db_data: Dict[str, Any]
    chart_request: Optional[Dict[str, Any]]
    chart_metadata: Optional[Dict[str, Any]]
    report_data: Optional[Dict[str, Any]]
    summary_text: str
    chat_response: Optional[str]
    ollama_prompt: str
    read_only: bool
    error: Optional[str]


def classifier_node(state: CMSGraphState) -> Dict[str, Any]:
    """Analyzes intent and entities, then routes to appropriate sub-graph."""
    query = state.get("user_query", "").strip()
    mem_ctx = state.get("memory_context")
    clean_q = query.lower()

    intent, entities = parse_intent_and_entities(query, memory_context=mem_ctx)

    # 1. Conversational Fast Route
    if intent in (INTENT_GREETING, INTENT_HELP):
        return {"intent": intent, "entities": entities, "route": "conversational"}

    # 2. Check for explicit chart/graph render request vs explanation
    is_explanation = any(w in clean_q for w in ["explain", "what is", "what are", "how is", "how does", "tell me about", "meaning", "guide", "analogy"])
    EXPLICIT_CHART_ACTION_WORDS = ["show", "generate", "render", "display", "plot", "draw", "create", "make"]
    CHART_TYPE_WORDS = ["graph", "chart", "pie", "bar", "line", "donut", "doughnut", "column", "area"]
    is_render_request = (
        intent == INTENT_DYNAMIC_CHART
        or (
            any(w in clean_q for w in EXPLICIT_CHART_ACTION_WORDS)
            and any(w in clean_q for w in CHART_TYPE_WORDS)
        )
    )

    if is_render_request and not is_explanation:
        return {"intent": intent, "entities": entities, "route": "chart"}

    # 3. Check for Vector RAG semantic knowledge inquiry
    has_knowledge_kw = any(kw in clean_q for kw in KNOWLEDGE_KEYWORDS) or is_explanation
    has_specific_filter = bool(entities.get("item_filter") or entities.get("unit_filter"))

    if has_knowledge_kw and not has_specific_filter:
        return {"intent": intent, "entities": entities, "route": "vector_rag"}
    elif has_knowledge_kw and has_specific_filter:
        return {"intent": intent, "entities": entities, "route": "hybrid"}

    # 4. Standard Database query
    return {"intent": intent, "entities": entities, "route": "sql_db"}


def conversational_node(state: CMSGraphState) -> Dict[str, Any]:
    """Handles fast greetings, help, and role assistance."""
    query = state.get("user_query", "")
    chat_res = ChatTool.execute(query)
    resp = chat_res.get("response", "Hello! How can I assist you with CMS today?")
    return {
        "chat_response": resp,
        "summary_text": resp,
        "db_data": {},
        "rag_context": "",
        "retrieved_docs": [],
        "read_only": True
    }


def vector_retrieval_node(state: CMSGraphState) -> Dict[str, Any]:
    """Retrieves relevant domain knowledge chunks from the vector database using embeddings."""
    query = state.get("user_query", "")
    vector_db = get_vector_db()

    scored_docs = vector_db.similarity_search_with_score(query, k=3)
    retrieved = []
    context_parts = []

    for doc, score in scored_docs:
        title = doc.metadata.get("title", "CMS Knowledge Document")
        retrieved.append({
            "title": title,
            "category": doc.metadata.get("category", "general"),
            "source": doc.metadata.get("source", "knowledge_base"),
            "similarity_score": round(score, 3)
        })
        if score >= 0.20:
            context_parts.append(f"[{title}] (Confidence: {score:.2f}):\n{doc.page_content.strip()}")

    rag_context = "\n\n".join(context_parts) if context_parts else ""

    return {
        "retrieved_docs": retrieved,
        "rag_context": rag_context
    }


def database_query_node(state: CMSGraphState) -> Dict[str, Any]:
    """Queries the live CMS database using indexed fast paths or LangChain SQL generation."""
    query = state.get("user_query", "")
    intent = state.get("intent", "INVENTORY_SUMMARY")
    entities = state.get("entities", {})

    db_data = {}

    if intent in STANDARD_DB_INTENTS:
        db_result = DatabaseTool.execute(intent=intent, entities=entities, prompt=query)
        db_data = db_result.get("data", {})
    else:
        chain_info = LangChainSQLChain.run_query(query, intent=intent, entities=entities)
        sql_records = chain_info.get("db_result", {}).get("records")

        if chain_info.get("sql_valid") and sql_records is not None and len(sql_records) > 0:
            db_data = {
                "source": "LangChainSQLChain",
                "generated_sql": chain_info.get("generated_sql"),
                "records": sql_records,
                "total_count": len(sql_records)
            }
        else:
            db_result = DatabaseTool.execute(intent=intent, entities=entities, prompt=query)
            db_data = db_result.get("data", {})
            if chain_info.get("generated_sql"):
                db_data["generated_sql"] = chain_info.get("generated_sql")

    return {"db_data": db_data, "read_only": True, "route": state.get("route", "sql_db")}


def visualization_node(state: CMSGraphState) -> Dict[str, Any]:
    """Executes ChartTool or ReportTool on fetched database records."""
    query = state.get("user_query", "")
    intent = state.get("intent", "DYNAMIC_CHART")
    db_data = state.get("db_data", {})
    clean_q = query.lower()

    report_data = None
    if intent == INTENT_REPORT_GEN or "report" in clean_q:
        report_data = ReportTool.execute(intent=intent, db_data=db_data, prompt=query)

    chart_result = ChartTool.execute(intent=intent, db_data=db_data, prompt=query)

    return {
        "report_data": report_data,
        "chart_request": chart_result.get("chart_request"),
        "chart_metadata": chart_result.get("chart_metadata")
    }


def synthesis_node(state: CMSGraphState) -> Dict[str, Any]:
    """Synthesizes structured summary and constructs grounded Ollama prompt with vector RAG context."""
    query = state.get("user_query", "")
    intent = state.get("intent", "GENERAL")
    db_data = state.get("db_data", {})
    rag_context = state.get("rag_context", "")
    chart_request = state.get("chart_request")
    route = state.get("route", "sql_db")

    summary_text = ""
    if route == "vector_rag" and rag_context:
        # Construct summary directly from top vector match
        docs = state.get("retrieved_docs", [])
        top_title = docs[0].get("title", "CMS Knowledge") if docs else "CMS Reference"
        # Take first 2 sentences from the top match as summary fallback
        sentences = [s.strip() for s in rag_context.split("\n") if s.strip() and not s.startswith("[")]
        summary_text = " • " + "\n • ".join(sentences[:3]) if sentences else rag_context[:300]
    else:
        summary_res = SummaryTool.execute(intent=intent, db_data=db_data)
        summary_text = summary_res.get("summary_text", "")

    # Build comprehensive grounded Ollama prompt
    ollama_prompt = build_ollama_prompt(
        user_query=query,
        intent=intent,
        db_context=db_data,
        chart_request=chart_request,
        rag_context=rag_context
    )

    return {
        "summary_text": summary_text,
        "ollama_prompt": ollama_prompt
    }


def _build_workflow() -> StateGraph:
    """Builds and compiles the LangGraph StateGraph workflow."""
    builder = StateGraph(CMSGraphState)

    # 1. Add all workflow nodes
    builder.add_node("classifier", classifier_node)
    builder.add_node("conversational", conversational_node)
    builder.add_node("vector_retrieval", vector_retrieval_node)
    builder.add_node("database_query", database_query_node)
    builder.add_node("visualization", visualization_node)
    builder.add_node("synthesis", synthesis_node)

    # 2. Add entry edge
    builder.add_edge(START, "classifier")

    # 3. Add conditional routing edges from classifier
    builder.add_conditional_edges(
        "classifier",
        lambda s: s.get("route", "sql_db"),
        {
            "conversational": "conversational",
            "vector_rag": "vector_retrieval",
            "sql_db": "database_query",
            "hybrid": "vector_retrieval",
            "chart": "database_query"
        }
    )

    # 4. Wire edges for each sub-path
    builder.add_edge("conversational", END)

    # vector_rag: vector_retrieval -> synthesis -> END
    builder.add_edge("vector_retrieval", "synthesis")

    # sql_db: database_query -> synthesis -> END (no chart generation)
    # chart:  database_query -> visualization -> synthesis -> END
    builder.add_conditional_edges(
        "database_query",
        lambda s: "visualization" if s.get("route") == "chart" else "synthesis",
        {
            "visualization": "visualization",
            "synthesis": "synthesis"
        }
    )

    builder.add_edge("visualization", "synthesis")
    builder.add_edge("synthesis", END)

    return builder.compile()


# Compile global LangGraph instance
_compiled_graph = None


def get_langgraph_agent():
    """Returns singleton compiled LangGraph executable."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_workflow()
    return _compiled_graph


class LangGraphCMSAgent:
    """Public interface for interacting with the LangGraph CMS Agent."""

    @classmethod
    def process_request(
        cls,
        user_query: str,
        session_id: str = "default_user",
        user_role: str = "Guest",
        memory_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the LangGraph state graph for the given user request.
        Returns the finalized state dictionary.
        """
        graph = get_langgraph_agent()
        initial_state: CMSGraphState = {
            "user_query": user_query,
            "session_id": session_id,
            "user_role": user_role,
            "memory_context": memory_context or {},
            "retrieved_docs": [],
            "rag_context": "",
            "db_data": {},
            "read_only": True
        }

        # For hybrid route, we execute vector retrieval and then database query
        clean_q = user_query.lower()
        intent, entities = parse_intent_and_entities(user_query, memory_context=memory_context)
        has_knowledge_kw = any(kw in clean_q for kw in KNOWLEDGE_KEYWORDS)
        has_specific_filter = bool(entities.get("item_filter") or entities.get("unit_filter"))

        if has_knowledge_kw and has_specific_filter:
            # Hybrid execution: first vector retrieval then database query
            v_res = vector_retrieval_node(initial_state)
            initial_state.update(v_res)
            db_res = database_query_node({"user_query": user_query, "intent": intent, "entities": entities})
            initial_state.update(db_res)
            synth_res = synthesis_node({**initial_state, "route": "hybrid", "intent": intent})
            initial_state.update(synth_res)
            initial_state["intent"] = intent
            initial_state["entities"] = entities
            initial_state["route"] = "hybrid"
            return initial_state

        result_state = graph.invoke(initial_state)
        return result_state
