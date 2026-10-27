"""
Vector Database Module for CMS AI Assistant.
Provides persistent vector storage, embedding generation, semantic similarity search,
and knowledge retrieval for LangChain and LangGraph workflows.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from langchain_core.documents import Document
from aiml.chatbot.embeddings import CMSEmbeddings, CMSDenseEmbeddings

VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "vector_db")
VECTOR_DB_FILE = os.path.join(VECTOR_DB_DIR, "knowledge_store.json")


# Curated CMS Core Knowledge Corpus for Ingestion
CMS_KNOWLEDGE_DOCUMENTS = [
    {
        "id": "doc_cat_policies",
        "title": "CMS Clothing Categories: CAT-I vs CAT-II Policy",
        "content": (
            "Clothing Management System categorizes items into CAT-I and CAT-II. "
            "CAT-I comprises personal clothing items issued directly to individuals for personal wear and life-cycle retention "
            "(e.g., combat shirts, uniforms, trousers, socks, berets, badges, rank insignias). "
            "CAT-II comprises unit-held communal and tactical equipment retained on unit inventory charge "
            "(e.g., heavy weather parkas, combat helmets, tents, specialized high-altitude boots, load-bearing vests). "
            "CAT-II items must be returned to unit quartermaster stores when operations conclude or personnel transfer."
        ),
        "metadata": {"category": "policy", "source": "CMS Standard Operating Procedures"}
    },
    {
        "id": "doc_stock_terminology",
        "title": "CMS Inventory Terminology: AUTH, Held, Reserve, Deficiency",
        "content": (
            "Key inventory metrics in CMS:\n"
            "- AUTH (Authorized Scale): The official mandated quantity of an item a unit or formation is permitted to hold.\n"
            "- Held (Stock Held): Active equipment currently present in unit warehouse, split into SER (Serviceable) and PWS (Partially Working State).\n"
            "- Res (Reserve Stock): Central backup pool at Division or DOU, split into Res SER and Res PWS.\n"
            "- Total Stock: Sum of Reserve Stock (SER + PWS) and Stock Held (SER + PWS).\n"
            "- Deficiency (DEFI): The deficit calculated as Authorized Scale minus Total Stock Held (DEFI = AUTH - Held). "
            "A positive deficiency indicates missing equipment that must be demanded from SCME."
        ),
        "metadata": {"category": "inventory", "source": "CMS Inventory Manual"}
    },
    {
        "id": "doc_hierarchy_roles",
        "title": "CMS Military Hierarchy and User Role Responsibilities",
        "content": (
            "The CMS organizational tree is structured as ORD -> Division -> Brigade -> Unit.\n"
            "- ORD (Super Admin): System administrator managing the overall organization tree, user creation, and top-level analytics.\n"
            "- Division Admin: Oversees subordinate brigades and units, manages Division Reserve Stock (Res SER/PWS), and issues stock to units.\n"
            "- Brigade Admin: Monitors brigade-level readiness, aggregate unit inventory, and supply flow.\n"
            "- Unit Admin / Quartermaster: Tracks unit-held items, logs personnel strength, monitors deficiencies, and submits item demands.\n"
            "- SCME: Central equipment depot and catalog manager responsible for introducing catalog items, adding bulk stock, and issuing monthly ECC statements."
        ),
        "metadata": {"category": "hierarchy", "source": "CMS User Guide"}
    },
    {
        "id": "doc_accounting_units",
        "title": "Accounting Units (A/U): Nos vs Prs",
        "content": (
            "Items in the CMS catalog are counted by specific Accounting Units (A/U):\n"
            "- Nos (Numbers / Units): Single individual items such as combat jackets, shirts, helmets, berets, web belts, altimeters.\n"
            "- Prs (Pairs): Items supplied and issued in matched sets of two, such as combat boots, wool socks, tactical gloves, insoles.\n"
            "All inventory statements, issue vouchers, and demand slips must specify the correct A/U to prevent quantity mismatches."
        ),
        "metadata": {"category": "catalog", "source": "CMS Catalog Standards"}
    },
    {
        "id": "doc_graph_productive_analysis",
        "title": "Dashboard Graph 1: Productive Analysis (3D Grouped Bar Chart)",
        "content": (
            "The Productive Analysis graph is a 3D Grouped Bar Chart comparing three quantities side-by-side for each unit:\n"
            "1. Authorized Scale (what the unit is mandated to have),\n"
            "2. Held (what the unit currently holds in stores),\n"
            "3. Deficiency (shortfall: Authorized - Held).\n"
            "Managers use this chart to rapidly identify units suffering the widest equipment deficits across key equipment items."
        ),
        "metadata": {"category": "graphs", "source": "graph_readme.md"}
    },
    {
        "id": "doc_graph_global_fulfillment",
        "title": "Dashboard Graph 2: Global Fulfillment (3D Donut Chart)",
        "content": (
            "The Global Fulfillment graph is a 3D circular Donut Chart displaying overall system-wide stock availability.\n"
            "It computes the percentage of total authorized clothing currently held across all formations: (Total Held / Total Auth) * 100%.\n"
            "The center percentage indicates base-wide health, with green representing stocked goods and red representing unfulfilled deficiencies."
        ),
        "metadata": {"category": "graphs", "source": "graph_readme.md"}
    },
    {
        "id": "doc_graph_top_deficiencies",
        "title": "Dashboard Graph 3: Top 5 Deficient Items (3D Horizontal Bar Chart)",
        "content": (
            "The Top 5 Deficient Items graph ranks the 5 specific clothing articles with the highest cumulative shortages system-wide.\n"
            "Items with the longest bars represent urgent procurement priorities for SCME supply officers to restock first."
        ),
        "metadata": {"category": "graphs", "source": "graph_readme.md"}
    },
    {
        "id": "doc_graph_deficiency_share",
        "title": "Dashboard Graph 4: Deficiency Share by Unit (3D Pie Chart)",
        "content": (
            "The Deficiency Share by Unit graph is a 3D Pie Chart showing the percentage proportion of total system shortage that belongs to each individual military unit.\n"
            "If Unit A accounts for 50% of the pie, half of the total missing equipment in the formation is concentrated in Unit A."
        ),
        "metadata": {"category": "graphs", "source": "graph_readme.md"}
    },
    {
        "id": "doc_graph_au_split",
        "title": "Dashboard Graph 5: Accounting Unit Quantity Split (3D Column Chart)",
        "content": (
            "The A/U Split chart categorizes held stock by unit of measurement: Nos (individual items like jackets, helmets) versus Prs (pairs like boots, gloves).\n"
            "It provides supply chain logistics insight into handling single-piece garments versus paired accessories."
        ),
        "metadata": {"category": "graphs", "source": "graph_readme.md"}
    },
    {
        "id": "doc_graph_readiness",
        "title": "Dashboard Graph 6: Supply Readiness by Unit (3D Color-Coded Column Chart)",
        "content": (
            "Supply Readiness is calculated per unit as (Held / Authorized) * 100% and rendered in 3D color-coded columns:\n"
            "- Green (>= 80%): Excellent readiness / fully operational.\n"
            "- Amber (50% - 79%): Warning state / needs replenishment.\n"
            "- Red (< 50%): Critical deficiency / urgent supply action required."
        ),
        "metadata": {"category": "graphs", "source": "graph_readme.md"}
    },
    {
        "id": "doc_schema_tables",
        "title": "CMS Database Architecture and Usable Tables",
        "content": (
            "CMS relational database schema includes:\n"
            "- clothing_items: Catalog defining item name, category (CAT-I, CAT-II), accounting unit (Nos, Prs), and specifications.\n"
            "- inventory: Warehouse stock tracking held quantities (SER, PWS) per unit and item.\n"
            "- units: Organizational hierarchy nodes (Division, Brigade, Unit).\n"
            "- users: System user credentials, ranks, and assigned roles (ORD, Division Admin, Unit Admin, SCME).\n"
            "- demands: Electronic replenishment requests raised by units.\n"
            "- sales / issuances: Records of clothing issued or sold to personnel.\n"
            "- authorizations: Authorized scale limits configured per unit and item."
        ),
        "metadata": {"category": "schema", "source": "CMS Database Architecture"}
    },
    {
        "id": "doc_export_formats",
        "title": "CMS Data Export Capabilities (CSV, Excel, PDF)",
        "content": (
            "The AI Assistant and CMS dashboards support multi-format exports for session data:\n"
            "- CSV: Raw comma-separated data suitable for data analysis scripts.\n"
            "- Excel (XLS): Tab-separated spreadsheet format compatible with Microsoft Excel and Google Sheets.\n"
            "- PDF / HTML: Print-ready formatted document with headers, table borders, and CMS metadata.\n"
            "Users can request 'Export data as Excel' or click export action buttons."
        ),
        "metadata": {"category": "features", "source": "CMS Feature Manual"}
    }
]


class CMSVectorDatabase:
    """
    Persistent Vector Database for CMS AI Assistant.
    Stores LangChain Documents with dense embedding vectors and enables
    semantic retrieval, MMR, and metadata-filtered querying.
    """

    def __init__(self, storage_path: str = VECTOR_DB_FILE):
        self.storage_path = storage_path
        self.embeddings = CMSEmbeddings()
        self.documents: List[Document] = []
        self.vectors: np.ndarray = np.empty((0, CMSDenseEmbeddings.DIMENSION), dtype=np.float32)
        self.doc_ids: List[str] = []

        self._ensure_initialized()

    def _ensure_initialized(self):
        """Loads vector store from disk or ingests default knowledge corpus."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if os.path.exists(self.storage_path):
            self.load()
        else:
            self.ingest_default_knowledge()

    def ingest_default_knowledge(self):
        """Ingests default curated CMS knowledge documents."""
        docs = []
        for item in CMS_KNOWLEDGE_DOCUMENTS:
            doc = Document(
                page_content=item["content"],
                metadata={
                    "id": item["id"],
                    "title": item["title"],
                    **item.get("metadata", {})
                }
            )
            docs.append(doc)
        self.add_documents(docs)
        self.save()

    def add_documents(self, docs: List[Document]):
        """Embeds and indexes documents in the vector database."""
        if not docs:
            return

        texts = [d.page_content for d in docs]
        new_vecs = self.embeddings.embed_documents(texts)
        new_vecs_arr = np.array(new_vecs, dtype=np.float32)

        for i, doc in enumerate(docs):
            doc_id = doc.metadata.get("id", f"doc_{len(self.documents) + i}")
            self.doc_ids.append(doc_id)
            self.documents.append(doc)

        if self.vectors.size == 0:
            self.vectors = new_vecs_arr
        else:
            self.vectors = np.vstack([self.vectors, new_vecs_arr])

        self.save()

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 3,
        category_filter: Optional[str] = None
    ) -> List[Tuple[Document, float]]:
        """
        Calculates cosine similarity between query embedding and all indexed document vectors.
        Returns top-k documents with similarity scores in [0.0, 1.0].
        """
        if len(self.documents) == 0 or self.vectors.size == 0:
            return []

        q_vec = np.array(self.embeddings.embed_query(query), dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 1e-8:
            q_vec = q_vec / q_norm

        # Cosine similarity is the dot product of normalized vectors
        scores = np.dot(self.vectors, q_vec)

        # Apply category filter if specified
        valid_indices = []
        for idx, doc in enumerate(self.documents):
            if category_filter:
                doc_cat = doc.metadata.get("category", "")
                if doc_cat.lower() != category_filter.lower():
                    continue
            valid_indices.append(idx)

        if not valid_indices:
            return []

        # Sort filtered indices by score descending
        sorted_indices = sorted(valid_indices, key=lambda idx: scores[idx], reverse=True)
        top_k_indices = sorted_indices[:k]

        results = []
        for idx in top_k_indices:
            results.append((self.documents[idx], float(scores[idx])))

        return results

    def similarity_search(
        self,
        query: str,
        k: int = 3,
        category_filter: Optional[str] = None
    ) -> List[Document]:
        """Returns top-k most relevant Documents matching the query."""
        scored = self.similarity_search_with_score(query, k=k, category_filter=category_filter)
        return [doc for doc, _ in scored]

    def get_relevant_context(
        self,
        query: str,
        k: int = 2,
        min_score: float = 0.25
    ) -> str:
        """
        Returns a formatted knowledge context block for prompt augmentation.
        Omits low-confidence matches.
        """
        scored = self.similarity_search_with_score(query, k=k)
        relevant_blocks = []

        for doc, score in scored:
            if score >= min_score:
                title = doc.metadata.get("title", "CMS Knowledge Reference")
                relevant_blocks.append(f"[{title}] (Relevance: {score:.2f})\n{doc.page_content.strip()}")

        if not relevant_blocks:
            return ""

        return "\n\n".join(relevant_blocks)

    def save(self):
        """Persists indexed documents and vectors to disk."""
        data = {
            "doc_ids": self.doc_ids,
            "documents": [
                {
                    "page_content": d.page_content,
                    "metadata": d.metadata
                }
                for d in self.documents
            ],
            "vectors": self.vectors.tolist()
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Loads indexed documents and vectors from disk."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.doc_ids = data.get("doc_ids", [])
            self.documents = [
                Document(page_content=item["page_content"], metadata=item.get("metadata", {}))
                for item in data.get("documents", [])
            ]
            vec_list = data.get("vectors", [])
            if vec_list:
                self.vectors = np.array(vec_list, dtype=np.float32)
            else:
                self.vectors = np.empty((0, CMSDenseEmbeddings.DIMENSION), dtype=np.float32)
        except Exception as e:
            print(f"Failed to load vector store from {self.storage_path}: {e}. Re-ingesting...")
            self.ingest_default_knowledge()


# Global Singleton Vector Database instance
_vector_db_instance: Optional[CMSVectorDatabase] = None


def get_vector_db() -> CMSVectorDatabase:
    """Returns singleton instance of CMSVectorDatabase."""
    global _vector_db_instance
    if _vector_db_instance is None:
        _vector_db_instance = CMSVectorDatabase()
    return _vector_db_instance
