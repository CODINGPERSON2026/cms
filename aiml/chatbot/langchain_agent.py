"""
LangChain Agent Module for CMS AI Assistant.
Orchestrates natural language understanding, LangChain SQL Database queries, and Ollama synthesis.
"""

from typing import Dict, Any, Optional
from aiml.chatbot.sql_chain import LangChainSQLChain, validate_read_only_sql
from aiml.chatbot.database_tool import DatabaseTool
from aiml.chatbot.prompt import CMS_SYSTEM_PROMPT, build_ollama_prompt


STANDARD_DB_INTENTS = {
    "PRODUCT_INFO", "INVENTORY_SUMMARY", "USER_INFO", "CATEGORY_COMPARISON",
    "LOW_STOCK_DEFICIENCY", "SALES_ISSUANCE", "AUTHORIZATION_INFO",
    "RESERVE_STOCK", "REPORT_GEN", "UNIT_INFO", "DOU_INFO"
}


class LangChainCMSAgent:
    """
    LangChain Agent interfacing user queries with safe live database retrieval and Ollama LLM response generation.
    Optimized for high-performance sub-2-second response latency.
    """

    @classmethod
    def process_request(
        cls,
        user_query: str,
        intent: str,
        entities: Dict[str, Any],
        memory_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Processes a natural language request through LangChain database tools.
        Uses Fast-Path DatabaseTool execution for standard intents and dynamic LangChain SQL for custom queries.
        """
        chain_info = {}
        db_data = {}

        # 1. Fast-Path Optimization: For recognized standard database intents, execute direct indexed query (2-5ms)
        if intent in STANDARD_DB_INTENTS:
            db_result = DatabaseTool.execute(intent=intent, entities=entities, prompt=user_query)
            db_data = db_result.get("data", {})
            chain_info = {
                "query": user_query,
                "intent": intent,
                "table_names": LangChainSQLChain.get_usable_table_names(),
                "entities": entities,
                "generated_sql": None,
                "sql_valid": True,
                "read_only": True
            }
        else:
            # 2. Dynamic LangChain SQL Generation & Execution for unclassified or complex custom queries
            chain_info = LangChainSQLChain.run_query(user_query, intent=intent, entities=entities)
            sql_records = chain_info.get("db_result", {}).get("records")

            if chain_info.get("sql_valid") and sql_records is not None and len(sql_records) > 0:
                db_data = {
                    "source": "LangChainSQLChain",
                    "generated_sql": chain_info.get("generated_sql"),
                    "records": sql_records,
                    "total_count": len(sql_records)
                }
            else:
                db_result = DatabaseTool.execute(intent=intent, entities=entities, prompt=user_query)
                db_data = db_result.get("data", {})
                if chain_info.get("generated_sql"):
                    db_data["generated_sql"] = chain_info.get("generated_sql")

        # 3. Construct Ollama grounded prompt payload
        ollama_prompt = build_ollama_prompt(
            user_query=user_query,
            intent=intent,
            db_context=db_data
        )

        return {
            "intent": intent,
            "entities": entities,
            "chain_info": chain_info,
            "db_data": db_data,
            "ollama_prompt": ollama_prompt,
            "read_only": True
        }


