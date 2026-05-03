import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.parser import CodeParser
from backend.rag.vector_store import VectorStore

if __name__ == "__main__":
    repo_path = "repos/Whatsapp-Chat-Analyzer"  

    # Step 1: Parse repo
    parser = CodeParser(language="python")
    parsed_data = parser.parse_repository(repo_path)

    print(f"Parsed {len(parsed_data)} chunks")

    # Step 2: Build vector DB
    store = VectorStore()
    store.build_index(parsed_data)

    # Step 3: Query
    query = "fix helper.py file in my repo"

    results = store.search(query, top_k=3)

    print("\n🔍 Top Results:\n")

    for r in results:
        print("=" * 50)
        print("File:", r["file"])
        print("Code:\n", r["code"][:200])