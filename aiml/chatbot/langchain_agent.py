"""
LangChain Agent Module for CMS AI Assistant.
Orchestrates natural language understanding, LangChain SQL Database queries, and Ollama synthesis.
"""

from typing import Dict, Any, Optional
from aiml.chatbot.sql_chain import LangChainSQLChain, validate_read_only_sql
from aiml.chatbot.database_tool import DatabaseTool
from aiml.chatbot.prompt import CMS_SYSTEM_PROMPT, build_ollama_prompt


class LangChainCMSAgent:
    """
    LangChain Agent interfacing user queries with safe live database retrieval and Ollama LLM response generation.
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
        """
        # 1. Prepare LangChain SQL database context
        chain_info = LangChainSQLChain.run_query(user_query, intent=intent, entities=entities)

        # 2. Retrieve live database records safely via DatabaseTool
        db_result = DatabaseTool.execute(intent=intent, entities=entities, prompt=user_query)
        db_data = db_result.get("data", {})

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
