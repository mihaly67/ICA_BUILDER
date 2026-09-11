import os
import sqlite3
import faiss
import numpy as np
import torch
import sys
from sentence_transformers import SentenceTransformer

WORK_DIR = "/home/Jules/RAG_epito_ismeretek"
DB_FILE = os.path.join(WORK_DIR, "rag_knowledge.db")
INDEX_FILE = os.path.join(WORK_DIR, "rag_vectors.index")

def main():
    if len(sys.argv) < 2:
        print("Kérlek, adj meg egy keresési kifejezést!")
        print('Példa: python3 rag_learner.py "How to build a GraphRAG system"')
        return

    query = " ".join(sys.argv[1:])
    top_k = 10

    print(f"🔍 Keresés a RAG adatbázisban: '{query}'")

    # 1. Adatbázisok betöltése
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        index = faiss.read_index(INDEX_FILE)
    except Exception as e:
        print(f"❌ Hiba a fájlok betöltésekor: {e}")
        return

    # 2. Modell betöltése
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

    # 3. Keresés
    q_vec = model.encode([query], normalize_embeddings=True)
    distances, indices = index.search(np.array(q_vec).astype('float32'), top_k)

    print("\n" + "="*80)
    print("🧠 TANULÁSI EREDMÉNYEK (Legjobb kontextusok)")
    print("="*80)

    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        cursor.execute("SELECT source_repo, filepath, content FROM rag_data WHERE id=?", (int(idx),))
        res = cursor.fetchone()
        if res:
            repo, path, content = res
            print(f"\n[{i+1}] REPO: {repo} | FILE: {path} | DISTANCE: {dist:.4f}")
            print("-" * 60)
            # A találat tartalmát rövidítve vagy egyben kiírjuk
            print(content.strip())
            print("-" * 60)

    conn.close()

if __name__ == "__main__":
    main()
