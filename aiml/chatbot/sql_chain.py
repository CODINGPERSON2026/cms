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
    Inspects database schema dynamically, generates safe read-only SQL queries using LangChain + Ollama,
    and executes them securely against the CMS database engine.
    Includes in-memory caching to ensure sub-second query response times.
    """
    _sql_db = None
    _llm = None
    _usable_tables = None
    _schema_cache = None

    @classmethod
    def get_sql_database(cls):
        """Lazy load and cache LangChain SQLDatabase wrapper for Flask SQLAlchemy engine."""
        if cls._sql_db is None:
            try:
                from langchain_community.utilities.sql_database import SQLDatabase
                cls._sql_db = SQLDatabase(db.engine)
            except Exception as e:
                print(f"Notice initializing LangChain SQLDatabase: {e}")
                return None
        return cls._sql_db

    @classmethod
    def get_llm(cls):
        """Initialize and cache LangChain ChatOllama model instance."""
        if cls._llm is None:
            try:
                from langchain_ollama import ChatOllama
                cls._llm = ChatOllama(model="llama3.2:latest", temperature=0)
            except Exception as e:
                try:
                    from langchain_community.chat_models import ChatOllama
                    cls._llm = ChatOllama(model="llama3.2:latest", temperature=0)
                except Exception as ex:
                    print(f"Notice initializing ChatOllama LLM: {ex}")
                    return None
        return cls._llm

    @classmethod
    def get_usable_table_names(cls) -> List[str]:
        """Dynamically inspect and cache available tables in the CMS database."""
        if cls._usable_tables is None:
            try:
                sql_db = cls.get_sql_database()
                if sql_db:
                    cls._usable_tables = sql_db.get_usable_table_names()
                else:
                    from sqlalchemy import inspect
                    inspector = inspect(db.engine)
                    cls._usable_tables = inspector.get_table_names()
            except Exception as e:
                print(f"Error inspecting table names: {e}")
                cls._usable_tables = ["login_users", "ecc_scme_items", "track_unit_items", "item_auth", "transactions", "divs", "fod_stock_table"]
        return cls._usable_tables

    @classmethod
    def get_schema_info(cls) -> str:
        """Cache schema reflection metadata to eliminate repetitive DB inspection latency."""
        if cls._schema_cache is None:
            try:
                sql_db = cls.get_sql_database()
                if sql_db:
                    usable = cls.get_usable_table_names()
                    # Limit schema context to top essential tables for fast LLM processing
                    top_tables = [t for t in usable if t in [
                        "ecc_scme_items", "track_unit_items", "transactions",
                        "scme_issued_items", "fod_stock_table", "login_users",
                        "units", "divs", "item_auth", "our_items"
                    ]] or usable[:8]
                    cls._schema_cache = sql_db.get_table_info(table_names=top_tables)
                else:
                    cls._schema_cache = ""
            except Exception as e:
                print(f"Error retrieving schema info: {e}")
                cls._schema_cache = ""
        return cls._schema_cache

    @classmethod
    def generate_sql(cls, user_query: str, table_names: Optional[List[str]] = None) -> Optional[str]:
        """
        Generates a read-only SQL SELECT query based on user natural language prompt and dynamic DB schema.
        """
        llm = cls.get_llm()
        if not llm:
            return None

        try:
            schema_info = cls.get_schema_info()

            system_prompt = (
                "You are an expert SQL assistant for MySQL. "
                "Convert the user question into a valid SQL SELECT query.\n"
                "RULES:\n"
                "1. Return ONLY the raw SQL query. No markdown formatting (no ```sql), no explanation.\n"
                "2. ONLY write SELECT or WITH queries. NEVER write INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or CREATE.\n"
                "3. Append 'LIMIT 50' to the query. Do NOT use semicolons (;).\n"
                "4. Use exact table and column names from this schema:\n\n"
                f"{schema_info}\n"
            )

            prompt = f"User Question: {user_query}\nSQL Query:"
            response = llm.invoke([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}])
            
            sql_candidate = response.content.strip() if hasattr(response, "content") else str(response).strip()
            # Clean potential markdown wrappers and semicolons
            sql_candidate = re.sub(r"^```(?:sql)?\s*", "", sql_candidate, flags=re.IGNORECASE)
            sql_candidate = re.sub(r"\s*```$", "", sql_candidate)
            sql_candidate = sql_candidate.strip()
            sql_candidate = re.sub(r";+\s*", " ", sql_candidate).strip()

            if validate_read_only_sql(sql_candidate):
                return sql_candidate
            else:
                print(f"Generated SQL failed read-only validation check: {sql_candidate}")
                return None
        except Exception as e:
            print(f"Error generating SQL via LangChain + ChatOllama: {e}")
            return None


    @classmethod
    def execute_sql(cls, sql_query: str) -> Dict[str, Any]:
        """
        Safely executes a validated read-only SQL query against the database engine.
        Returns dict containing records, column headers, and row count.
        """
        if not validate_read_only_sql(sql_query):
            return {"success": False, "error": "Query failed read-only security check.", "records": []}

        try:
            from sqlalchemy import text
            with db.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                keys = list(result.keys())
                rows = [dict(zip(keys, row)) for row in result.fetchmany(50)]

            return {
                "success": True,
                "sql_query": sql_query,
                "columns": keys,
                "records": rows,
                "row_count": len(rows),
                "error": None
            }
        except Exception as e:
            print(f"Error executing safe SQL query: {e}")
            return {
                "success": False,
                "sql_query": sql_query,
                "error": str(e),
                "records": []
            }

    @classmethod
    def run_query(cls, user_query: str, intent: str = "GENERAL", entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a complete LangChain database retrieval pipeline:
        Dynamic Schema Inspection -> Safe SQL Generation -> Read-Only Validation -> DB Execution.
        """
        entities = entities or {}
        table_names = cls.get_usable_table_names()
        
        # 1. Attempt dynamic SQL query generation via LangChain ChatOllama
        generated_sql = cls.generate_sql(user_query, table_names=table_names)
        
        db_exec_result = {}
        if generated_sql:
            db_exec_result = cls.execute_sql(generated_sql)

        return {
            "query": user_query,
            "intent": intent,
            "table_names": table_names,
            "entities": entities,
            "generated_sql": generated_sql,
            "sql_valid": bool(generated_sql and db_exec_result.get("success")),
            "db_result": db_exec_result,
            "read_only": True
        }

