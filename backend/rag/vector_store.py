import os
import faiss
import numpy as np
from typing import List, Dict
from tqdm import tqdm
from sentence_transformers import SentenceTransformer


class VectorStore:
    """
    FAISS-backed vector store for code chunk similarity search.
    Uses cosine similarity via L2-normalized embeddings + IndexFlatIP.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        # IndexFlatIP = inner product. With L2-normalized vectors → cosine similarity
        self.index = faiss.IndexFlatIP(self.dim)
        self.metadata: List[Dict] = []

    def _embed(self, text: str) -> np.ndarray:
        """
        Embed text and L2-normalize so IndexFlatIP computes cosine similarity.
        """
        vec = self.model.encode(text[:2000], convert_to_numpy=True).astype("float32")
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def get_embedding(self, text: str) -> List[float]:
        return self._embed(text).tolist()

    def build_index(self, parsed_data: List[Dict]):
        """
        Build FAISS index from parsed code chunks.
        """
        if not parsed_data:
            print("⚠️  No data to index.")
            return

        embeddings = []
        valid_items = []

        print("🔄 Generating embeddings...")
        for item in tqdm(parsed_data):
            try:
                emb = self._embed(item["code"])
                embeddings.append(emb)
                valid_items.append(item)
            except Exception as e:
                print(f"❌ Skipping item due to error: {e}")

        if not embeddings:
            print("⚠️  No embeddings generated.")
            return

        matrix = np.stack(embeddings).astype("float32")

        print("⚡ Building FAISS index...")
        self.index.add(matrix)
        self.metadata = valid_items

        print(f"✅ Indexed {len(self.metadata)} code chunks")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve top-k most similar code chunks for a query.
        """
        if self.index.ntotal == 0:
            print("⚠️  Index is empty. Call build_index() first.")
            return []

        query_emb = self._embed(query).reshape(1, -1)
        top_k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_emb, top_k)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(self.metadata):
                result = dict(self.metadata[idx])
                result["score"] = float(score)
                results.append(result)

        return results

    def save(self, path: str):
        """Persist index and metadata to disk."""
        import pickle
        faiss.write_index(self.index, f"{path}.faiss")
        with open(f"{path}.meta.pkl", "wb") as f:
            pickle.dump(self.metadata, f)
        print(f"💾 Saved index to {path}")

    def load(self, path: str):
        """Load index and metadata from disk."""
        import pickle
        self.index = faiss.read_index(f"{path}.faiss")
        with open(f"{path}.meta.pkl", "rb") as f:
            self.metadata = pickle.load(f)
        print(f"📂 Loaded index from {path} ({len(self.metadata)} chunks)")