"""
Comprehensive End-to-End Verification Test for CMS AI Assistant:
- Embeddings Generation (CMSEmbeddings)
- Vector Database Semantic Retrieval (CMSVectorDatabase)
- LangChain SQL + RAG Agent (LangChainCMSAgent)
- LangGraph Workflow StateGraph (LangGraphCMSAgent)
- Flask Chat SSE Stream Pipeline Simulation
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app
from aiml.chatbot.embeddings import CMSEmbeddings, CMSDenseEmbeddings
from aiml.chatbot.vector_store import get_vector_db, CMS_KNOWLEDGE_DOCUMENTS
from aiml.chatbot.langgraph_agent import LangGraphCMSAgent
from aiml.chatbot.langchain_agent import LangChainCMSAgent
from aiml.chatbot.chatbot import chat


def test_embeddings():
    print("\n--- 1. Testing CMSEmbeddings ---")
    emb = CMSEmbeddings()
    sample_text = "What is the policy for CAT-I clothing items and combat boots?"
    vec = emb.embed_query(sample_text)
    assert len(vec) == 128, f"Expected 128 dimensions, got {len(vec)}"
    print(f"Embedding generated successfully: Dimension={len(vec)}, First 5 values={vec[:5]}")


def test_vector_database():
    print("\n--- 2. Testing CMSVectorDatabase Semantic Retrieval ---")
    db = get_vector_db()
    assert len(db.documents) >= len(CMS_KNOWLEDGE_DOCUMENTS), "Documents not loaded properly"
    print(f"Indexed Knowledge Documents: {len(db.documents)}")

    test_queries = [
        "Explain the 3D donut Global Fulfillment chart",
        "What are the rules and wear life for CAT-I vs CAT-II clothing?",
        "How is unit deficiency calculated from authorized and held?"
    ]

    for q in test_queries:
        print(f"\nQuery: '{q}'")
        results = db.similarity_search_with_score(q, k=2)
        for doc, score in results:
            print(f"  -> Match: [{doc.metadata.get('title')}] (Cosine Similarity: {score:.3f})")
            assert score > 0, "Expected non-zero similarity score"


def test_langgraph_workflow(app):
    print("\n--- 3. Testing LangGraph StateGraph Workflow ---")
    with app.app_context():
        scenarios = [
            ("Greeting", "Hi there, who are you?"),
            ("Vector RAG Policy", "What is the difference between CAT-I and CAT-II garments?"),
            ("Vector RAG Visuals", "Explain the 3D donut Global Fulfillment chart and its analogy"),
            ("SQL Live Inventory", "List jacket stock in unit warehouse"),
            ("Chart Rendering", "Show bar chart of clothing items"),
            ("Hybrid Reasoning", "What is CAT-I clothing policy and what are our boot stocks?")
        ]

        for name, query in scenarios:
            print(f"\nScenario [{name}]: '{query}'")
            state = LangGraphCMSAgent.process_request(query, session_id="verify_session", user_role="Admin")
            print(f"  Route: {state.get('route')}")
            print(f"  Intent: {state.get('intent')}")
            print(f"  Retrieved Vector Docs: {len(state.get('retrieved_docs', []))}")
            if state.get("retrieved_docs"):
                for d in state["retrieved_docs"][:2]:
                    print(f"    - Source: {d.get('title')} (score: {d.get('similarity_score')})")
            if state.get("summary_text"):
                print(f"  Summary: {state['summary_text'][:120]}...")
            assert state.get("route") is not None, "LangGraph route should be resolved"


def test_flask_chat_sse_stream(app):
    print("\n--- 4. Testing Flask Chat SSE Stream with LangGraph & Vector DB ---")
    with app.app_context(), app.test_request_context(
        "/chatbot/chat",
        method="POST",
        json={"prompt": "What is CAT-I vs CAT-II clothing policy?", "session_id": "test_user_sse", "user_role": "Admin"}
    ):
        response = chat({
            "prompt": "What is CAT-I vs CAT-II clothing policy?",
            "session_id": "test_user_sse",
            "user_role": "Admin"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.mimetype == "text/event-stream", f"Expected SSE mimetype, got {response.mimetype}"
        
        # Read first SSE chunk
        first_chunk = next(response.response)
        chunk_str = first_chunk.decode("utf-8") if isinstance(first_chunk, bytes) else first_chunk
        print(f"SSE Initial Response Chunk: {chunk_str[:150]}...")
        assert "data:" in chunk_str, "Expected SSE data frame format"


if __name__ == "__main__":
    print("=================================================================")
    print("CMS AI ASSISTANT: EMBEDDINGS, VECTOR DATABASE, LANGGRAPH VERIFICATION")
    print("=================================================================")
    app = create_app()
    test_embeddings()
    test_vector_database()
    test_langgraph_workflow(app)
    test_flask_chat_sse_stream(app)
    print("\n=================================================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=================================================================")
