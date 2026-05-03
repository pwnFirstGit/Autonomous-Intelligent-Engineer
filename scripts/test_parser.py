import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.parser import CodeParser

if __name__ == "__main__":
    repo_path = r"D:\Autonomous-AI-Engineer\repos\Whatsapp-Chat-Analyzer"

    parser = CodeParser(language="python")

    results = parser.parse_repository(repo_path)

    print(f"Extracted {len(results)} elements\n")

    for item in results[:5]:
        print("=" * 50)
        print("Type:", item["type"])
        print("File:", item["file"])
        print("Lines:", item["start_line"], "-", item["end_line"])
        print(item["code"][:300])