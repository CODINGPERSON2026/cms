"""
Verification script for CMS AI Assistant.
Tests LangChain Integration, Read-Only Security Validator, Intent Parsing,
Query Routing, Database Query Building, Structured Chart Requests, Report Generation,
and Conversation Memory within an active Flask app context.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app
from aiml.chatbot.intent_parser import parse_intent_and_entities
from aiml.chatbot.sql_chain import validate_read_only_sql, LangChainSQLChain
from aiml.chatbot.query_router import QueryRouter
from aiml.chatbot.chart_formatter import build_chart_request
from aiml.chatbot.memory import ConversationMemory
from aiml.chatbot.auth import is_role_authorized, RESTRICT_ASSISTANT_ROLES


def run_tests():
    app = create_app()
    with app.app_context():
        print("=== Starting Comprehensive LangChain + Ollama CMS Verification Tests ===")

        # Test 1: Read-Only SQL Security Validator
        print("\n--- Test 1: Read-Only SQL Security Validator ---")
        test_sqls = [
            ("SELECT * FROM ecc_scme_items;", True),
            ("WITH summary AS (SELECT * FROM track_unit_items) SELECT * FROM summary;", True),
            ("INSERT INTO ecc_scme_items (item_name) VALUES ('Hacked');", False),
            ("UPDATE track_unit_items SET held = 9999 WHERE id = 1;", False),
            ("DELETE FROM login_users WHERE id = 1;", False),
            ("DROP TABLE login_users;", False),
            ("ALTER TABLE divs ADD COLUMN hack VARCHAR(255);", False),
            ("TRUNCATE TABLE transactions;", False)
        ]

        for sql, expected in test_sqls:
            is_valid = validate_read_only_sql(sql)
            status = "PASSED" if is_valid == expected else "FAILED"
            print(f"SQL: '{sql[:45]}...' => Valid Read-Only: {is_valid} (Expected: {expected}) -> {status}")
            assert is_valid == expected, f"Security validator failed for SQL: {sql}"

        # Test 2: Role-Based Authorization
        print("\n--- Test 2: Role-Based Authorization ---")
        roles_to_test = ["ORD", "Admin", "DOU", "Unit Users"]
        print(f"Current RESTRICT_ASSISTANT_ROLES setting: {RESTRICT_ASSISTANT_ROLES}")
        for r in roles_to_test:
            authorized = is_role_authorized(r)
            print(f"Role: '{r}' => Authorized: {authorized}")

        # Test 3: Natural Language Intent Parsing & Entity Extractions
        print("\n--- Test 3: Intent Parsing & Entity Extractions ---")
        prompt_cases = [
            "List logged in users",
            "Show all products",
            "How many products exist?",
            "Compare CAT-I and CAT-II",
            "Show Jacket inventory",
            "Show Sweater stock",
            "Which Unit has highest deficiency?",
            "Show issued items this month",
            "Show reserve stock",
            "Show serviceable stock",
            "Show authorization summary",
            "Display monthly inventory",
            "List all Units",
            "List all DOUs",
            "Show current inventory summary",
            "Generate inventory report"
        ]

        for p in prompt_cases:
            intent, entities = parse_intent_and_entities(p)
            print(f"Prompt: '{p}' => Intent: {intent}, Entities: {entities}")

        # Test 4: Dynamic Structured Chart Requests
        print("\n--- Test 4: Dynamic Structured Chart Requests ---")
        chart_prompts = [
            "Generate graph between CAT-I and CAT-II",
            "Pie chart of Jacket and Sweater",
            "Show highest deficiency",
            "Compare Units",
            "Monthly stock graph",
            "Monthly issue trend"
        ]

        for cp in chart_prompts:
            intent, entities = parse_intent_and_entities(cp)
            chart_req = build_chart_request(intent=intent, prompt=cp)
            print(f"Prompt: '{cp}' => Chart Request: {chart_req}")

        # Test 5: LangChain Query Router & Live Database Execution
        print("\n--- Test 5: LangChain Query Router & Live DB Execution ---")
        db_queries = [
            "List logged in users",
            "Show Jacket inventory",
            "Compare CAT-I and CAT-II",
            "Which Unit has highest deficiency?",
            "Show issued items this month",
            "Show reserve stock",
            "Show authorization summary",
            "Generate inventory report"
        ]

        for q in db_queries:
            intent, entities = parse_intent_and_entities(q)
            result = QueryRouter.route_query(intent=intent, entities=entities, prompt=q)
            print(f"\nQuery: '{q}'")
            print(f"Primary Tool Used: {result['primary_tool']}")
            print(f"Summary Text:\n{result['summary_text']}")
            if result.get("chart_request"):
                print(f"Chart Request Structure: {result['chart_request']}")

        # Test 6: Context-Aware Multi-turn Memory
        print("\n--- Test 6: Conversation Memory Context Awareness ---")
        session_id = "langchain_verification_session"

        # Turn 1
        turn1_prompt = "Show CAT-I products"
        intent1, entities1 = parse_intent_and_entities(turn1_prompt)
        ConversationMemory.update_session(session_id, turn1_prompt, intent1, "CAT-I products list", entities1.get("category_filter"))
        mem1 = ConversationMemory.get_session(session_id)

        print(f"Turn 1 Prompt: '{turn1_prompt}' => Intent: {intent1}, Memory State: {mem1['last_filter']}")

        # Turn 2
        turn2_prompt = "Only Jackets"
        intent2, entities2 = parse_intent_and_entities(turn2_prompt, memory_context=mem1)
        print(f"Turn 2 Follow-up: '{turn2_prompt}' => Retained Intent: {intent2}, Extracted Entities: {entities2}")

        print("\n=== Verification Completed Successfully! ===")


if __name__ == "__main__":
    run_tests()
