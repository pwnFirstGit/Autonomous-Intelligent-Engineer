from typing import List, Dict
import os


class CodeRetriever:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Get relevant code chunks using vector search.
        If the issue explicitly names a file, force that file into context.
        """
        vector_results = self.vector_store.search(query, top_k=top_k)
        explicit_results = self._retrieve_explicit_files(query)

        merged = []
        seen = set()
        for item in [*explicit_results, *vector_results]:
            key = (
                item.get("file"),
                item.get("start_line"),
                item.get("end_line"),
            )
            if key not in seen:
                merged.append(item)
                seen.add(key)

        return merged[:top_k]

    # def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
    
    #     return self._retrieve_explicit_files(query)

    def _retrieve_explicit_files(self, query: str) -> List[Dict]:
        query_lower = query.lower()
        matches = []

        for item in getattr(self.vector_store, "metadata", []):
            file_path = item.get("file", "")
            basename = os.path.basename(file_path).lower()
            stem = os.path.splitext(basename)[0]

            if basename and (basename in query_lower or stem in query_lower):
                matches.append(item)

        return matches
