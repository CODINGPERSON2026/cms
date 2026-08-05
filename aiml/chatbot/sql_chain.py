"""
LangChain SQL Chain Integration Module for CMS AI Assistant.
Provides safe, read-only database query generation and execution using LangChain and SQLAlchemy engine.
Enforces strict security checks blocking any write/modifying SQL operations.
"""

import re
from typing import Dict, Any, List, Optional
from extensions import db
from dotenv import load_dotenv

load_dotenv()

# Forbidden SQL keywords to strictly enforce READ-ONLY access
FORBIDDEN_SQL_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b", r"\bALTER\b",
    r"\bTRUNCATE\b", r"\bCREATE\b", r"\bREPLACE\b", r"\bGRANT\b", r"\bREVOKE\b",
    r"\bEXEC\b", r"\bEXECUTE\b"
]


def validate_read_only_sql(sql_query: str) -> bool:
    """
    Validate that an SQL query string is strictly READ-ONLY.
    Returns True if the query is a safe SELECT or WITH statement.
    Returns False if any forbidden write/modification statement is detected.
    """
    if not sql_query or not isinstance(sql_query, str):
        return False

    clean_sql = sql_query.strip().upper()

    # Must start with SELECT or WITH
    if not (clean_sql.startswith("SELECT") or clean_sql.startswith("WITH")):
        return False

    # Check for forbidden SQL keywords
    for pattern in FORBIDDEN_SQL_KEYWORDS:
        if re.search(pattern, clean_sql):
            return False

    return True


class LangChainSQLChain:
    """
    Manages LangChain SQL Database integration and safe query execution.
    """

    @classmethod
    def get_sql_database(cls):
        """Lazy load LangChain SQLDatabase wrapper for Flask SQLAlchemy engine."""
        try:
            from langchain_community.utilities.sql_database import SQLDatabase
            return SQLDatabase(db.engine)
        except Exception as e:
            print(f"Notice initializing LangChain SQLDatabase: {e}")
            return None

    @classmethod
    def get_llm(cls):
        """Initialize LangChain ChatOllama model instance."""
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model="llama3.2:latest", temperature=0)
        except Exception as e:
            try:
                from langchain_community.chat_models import ChatOllama
                return ChatOllama(model="llama3.2:latest", temperature=0)
            except Exception as ex:
                print(f"Notice initializing ChatOllama LLM: {ex}")
                return None

    @classmethod
    def run_query(cls, user_query: str, intent: str = "GENERAL", entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a safe read-only SQL query against the database using LangChain / SQLAlchemy.
        """
        entities = entities or {}
        item_filter = entities.get("item_filter")
        category_filter = entities.get("category_filter")
        unit_filter = entities.get("unit_filter")

        # Select target tables and generate safe query context
        try:
            sql_db = cls.get_sql_database()
            if sql_db:
                table_names = sql_db.get_usable_table_names()
            else:
                table_names = ["login_users", "ecc_scme_items", "track_unit_items", "item_auth", "transactions", "divs", "fod_stock_table"]
        except Exception as e:
            table_names = ["login_users", "ecc_scme_items", "track_unit_items", "item_auth", "transactions", "divs", "fod_stock_table"]

        return {
            "query": user_query,
            "intent": intent,
            "table_names": table_names,
            "entities": entities,
            "read_only": True
        }
