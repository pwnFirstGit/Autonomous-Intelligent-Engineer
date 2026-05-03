import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.parser import CodeParser
from backend.rag.vector_store import VectorStore
from backend.rag.retriever import CodeRetriever
from backend.agents.planner import LLMPlanner  # Fix: was wrongly imported from retriever.py

if __name__ == "__main__":
    repo_path = "repos/Whatsapp-Chat-Analyzer"

    # Step 1: Parse
    print("📂 Parsing repository...")
    parser = CodeParser(language="python")
    parsed_data = parser.parse_repository(repo_path)
    print(f"✅ {len(parsed_data)} chunks parsed")

    # Step 2: Build vector store
    store = VectorStore()
    store.build_index(parsed_data)

    # Step 3: Retrieve
    retriever = CodeRetriever(store)
    query = "calculate statistics and message count"
    context = retriever.retrieve(query, top_k=3)

    print(f"\n🔍 Retrieved {len(context)} chunks for query: '{query}'")
    for c in context:
        print(f"  - {os.path.basename(c['file'])} (score: {c.get('score', 'N/A'):.4f})")

    # Step 4: Plan
    planner = LLMPlanner()
    issue = "Optimize message statistics calculation and fix inefficiency"
    plan = planner.generate_plan(issue, context)

    print("\n🔥 GENERATED PLAN:")
    print(plan)