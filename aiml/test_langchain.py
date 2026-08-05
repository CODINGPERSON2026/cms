import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from aiml.chatbot.sql_chain import LangChainSQLChain

app = create_app()

with app.app_context():
    print("Testing LangChain + Ollama + CMS Database connection...")
    
    tables = LangChainSQLChain.get_usable_table_names()
    print(f"Discovered Database Tables: {tables}")
    
    llm = LangChainSQLChain.get_llm()
    if llm:
        print("LangChain ChatOllama initialized successfully.")
        response = llm.invoke("Summarize CMS clothing management goals in 2 sentences.")
        print("Ollama Response:")
        print(response.content if hasattr(response, "content") else str(response))
    else:
        print("ChatOllama not available.")

    print("\nRunning test query generation & execution...")
    result = LangChainSQLChain.run_query("List up to 5 logged in users")
    print(f"Generated SQL: {result.get('generated_sql')}")
    print(f"DB Records Retrieved ({result.get('db_result', {}).get('row_count', 0)}):")
    for r in result.get('db_result', {}).get('records', [])[:5]:
        print("  -", r)