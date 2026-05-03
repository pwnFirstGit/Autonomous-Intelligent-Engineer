import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.retriever import CodeRetriever

class RetrieverAgent:
    def __init__(self, vector_store):
        self.retriever = CodeRetriever(vector_store)

    def run(self, query: str):
        """
        Retrieve relevant context for a given query
        """
        return self.retriever.retrieve(query)