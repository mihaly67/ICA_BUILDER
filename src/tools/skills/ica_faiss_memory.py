import faiss
import numpy as np
import sqlite3
import os
import json
from sentence_transformers import SentenceTransformer

DB_PATH = '/home/misi/Jules_ICA_Builder/ica_knowledge_graph.db'
FAISS_INDEX_PATH = '/home/misi/Jules_ICA_Builder/ica_knowledge_graph.faiss'

class FAISSGraphMemory:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        if os.path.exists(FAISS_INDEX_PATH):
            self.index = faiss.read_index(FAISS_INDEX_PATH)
        else:
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.embedding_dim))
            self.build_index()

    def build_index(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, name, description FROM entities WHERE description IS NOT NULL")
        rows = c.fetchall()
        conn.close()

        if not rows:
            return

        ids = []
        texts = []
        for r in rows:
            ids.append(r[0])
            texts.append(f"{r[1]}: {r[2]}")

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        self.index.add_with_ids(embeddings, np.array(ids, dtype=np.int64))
        faiss.write_index(self.index, FAISS_INDEX_PATH)

    def search(self, query, top_k=3):
        if self.index.ntotal == 0:
            return []

        query_emb = self.model.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_emb, top_k)

        results = []
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        for idx, dist in zip(indices[0], distances[0]):
            if idx == -1: continue
            c.execute("SELECT name, type, description FROM entities WHERE id = ?", (int(idx),))
            row = c.fetchone()
            if row:
                results.append({"name": row[0], "type": row[1], "description": row[2], "distance": float(dist)})

        conn.close()
        return results

    def add_node(self, node_id, name, description):
        text = f"{name}: {description}"
        emb = self.model.encode([text], convert_to_numpy=True)
        self.index.add_with_ids(emb, np.array([node_id], dtype=np.int64))
        faiss.write_index(self.index, FAISS_INDEX_PATH)
