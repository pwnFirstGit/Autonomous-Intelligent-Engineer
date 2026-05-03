import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.parser import CodeParser
from backend.rag.vector_store import VectorStore
from backend.agents.graph import AIAgentSystem

if __name__ == "__main__":
    repo_path = "repos/Whatsapp-Chat-Analyzer"

    # Step 1: Parse repo
    print("📂 Parsing repository...")
    parser = CodeParser(language="python")
    parsed = parser.parse_repository(repo_path)
    print(f"✅ Parsed {len(parsed)} code chunks")

    # Step 2: Build vector store
    store = VectorStore()
    store.build_index(parsed)

    # Step 3: Run agent
    agent = AIAgentSystem(store, repo_path)

    issue = "fix syntax errors in helper.py file do not focus on any other function or class just fix the syntax errors in helper.py file"
    result = agent.run(issue)

    # Step 4: Print plan
    print("\n📋 PLAN:")
    print(result["plan"])

    # Step 5: Print results — use correct key "result" not "diff"
    print("\n🔥 RESULTS:\n")
    for r in result["results"]:
        print("=" * 60)
        print(f"File: {r['file']}")
        fix = r["result"]
        print(f"Status: {fix.get('status')}")
        print(f"Attempts: {fix.get('attempts')}")

        if fix.get("status") == "success":
            print(f"Output:\n{fix.get('output', '')[:300]}")
            print(f"\nDiff:\n{fix.get('diff', '')[:1000]}")
        else:
            print(f"Error:\n{fix.get('error', 'Unknown')[:300]}")

    # Step 6: Optional PR creation (set create_pr=True and fill pr_config)
    result = agent.run(
        issue,
        create_pr=True,
        pr_config={
            "repo_url": "https://github.com/Hariom-Nagar211/Whatsapp-Chat-Analyzer",
            "repo_owner": "Hariom-Nagar211",
            "repo_name": "Whatsapp-Chat-Analyzer",
            "base_branch": "main",
        }
    )
    if result.get("pr"):
        print("\n🔗 PR:", result["pr"].get("html_url"))