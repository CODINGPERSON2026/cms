"""
Query Router Module for CMS AI Assistant.
Decides user query intent and routes natural language requests to LangChain Database Agent, Chart Tool, or Report Tool.
"""

from typing import Dict, Any
from aiml.chatbot.intent_parser import (
    INTENT_GREETING, INTENT_HELP, INTENT_DYNAMIC_CHART, INTENT_REPORT_GEN,
    INTENT_CATEGORY_COMPARISON, INTENT_LOW_STOCK_DEFICIENCY, INTENT_SALES_ISSUANCE,
    INTENT_PRODUCT_INFO, INTENT_INVENTORY_SUMMARY, INTENT_UNIT_INFO, INTENT_USER_INFO,
    INTENT_AUTHORIZATION_INFO, INTENT_RESERVE_STOCK
)
from aiml.chatbot.langchain_agent import LangChainCMSAgent
from aiml.chatbot.tools import ChatTool, ChartTool, ReportTool, SummaryTool


class QueryRouter:
    """Routes user queries to LangChain agent, database tools, chart tool, or report tool."""

    @staticmethod
    def route_query(
        intent: str,
        entities: Dict[str, Any],
        prompt: str,
        memory_context: Any = None
    ) -> Dict[str, Any]:
        """
        Executes query routing and tool execution workflow.
        """
        clean_prompt = prompt.lower()

        # 1. Conversational Route
        if intent in (INTENT_GREETING, INTENT_HELP):
            chat_res = ChatTool.execute(prompt)
            return {
                "intent": intent,
                "primary_tool": "ChatTool",
                "chat_response": chat_res["response"],
                "db_data": {},
                "chart_data": None,
                "summary_text": chat_res["response"]
            }

        # 2. LangChain Database Agent Execution
        agent_result = LangChainCMSAgent.process_request(
            user_query=prompt,
            intent=intent,
            entities=entities,
            memory_context=memory_context
        )
        db_data = agent_result.get("db_data", {})

        # 3. Report Tool Execution if report requested
        report_data = None
        if intent == INTENT_REPORT_GEN or "report" in clean_prompt:
            report_data = ReportTool.execute(intent=intent, db_data=db_data, prompt=prompt)

        # 4. Chart Tool Execution if visualization requested
        chart_result = None
        if (
            intent in (INTENT_DYNAMIC_CHART, INTENT_CATEGORY_COMPARISON, INTENT_LOW_STOCK_DEFICIENCY, INTENT_SALES_ISSUANCE, INTENT_PRODUCT_INFO)
            or any(kw in clean_prompt for kw in ["graph", "chart", "pie", "bar", "line", "plot", "compare"])
        ):
            chart_result = ChartTool.execute(intent=intent, db_data=db_data, prompt=prompt)

        # 5. Summary Text Aggregation
        summary_result = SummaryTool.execute(intent=intent, db_data=db_data)

        primary_tool = "LangChainDBAgent"
        if intent == INTENT_DYNAMIC_CHART:
            primary_tool = "ChartTool"
        elif intent == INTENT_REPORT_GEN:
            primary_tool = "ReportTool"

        return {
            "intent": intent,
            "primary_tool": primary_tool,
            "chat_response": None,
            "db_data": db_data,
            "report_data": report_data,
            "chart_request": chart_result.get("chart_request") if chart_result else None,
            "chart_metadata": chart_result.get("chart_metadata") if chart_result else None,
            "summary_text": summary_result.get("summary_text", ""),
            "read_only": True
        }
