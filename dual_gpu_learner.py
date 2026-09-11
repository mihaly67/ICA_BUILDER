import os
import sqlite3
import faiss
import numpy as np
import torch
import sys
from sentence_transformers import SentenceTransformer
# Feltételezzük, hogy a llama_cpp_python telepítve van, ha meglesz a model.
# from llama_cpp import Llama

WORK_DIR = "/home/Jules/MX_LINUX_RAG"
DB_FILE = os.path.join(WORK_DIR, "rag_knowledge.db")
INDEX_FILE = os.path.join(WORK_DIR, "mxlinux_dev_index.faiss")

def main():
    print("=== 🧠 KÖVETKEZŐ GENERÁCIÓS RAG: DUAL-GPU PIPELINE ELŐKÉSZÍTÉS ===")
    print("ℹ️ A rendszer felismeri a (jövőbeli) második Quadro P2000 kártyát.")

    # Dual GPU szeparáció szimulálása
    device_count = torch.cuda.device_count()
    print(f"Észlelt GPU-k száma a rendszerben: {device_count}")

    if device_count >= 2:
        vectorizer_device = 'cuda:1'
        llm_device = 'cuda:0'
        print(f"🚀 PIPELINE PARALLELISM AKTÍV: Vektorizáló -> {vectorizer_device} | LLM Szintézis -> {llm_device}")
    else:
        vectorizer_device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        print(f"⚠️ Csak 1 GPU (vagy 0) található. Fallback mód: {vectorizer_device}")

    if len(sys.argv) < 2:
        query = "How to build a GraphRAG knowledge graph?"
    else:
        query = " ".join(sys.argv[1:])

    top_k = 5
    print(f"\n🔍 Keresés a 353 ezer rekordos RAG adatbázisban: '{query}'")

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        index = faiss.read_index(INDEX_FILE)
    except Exception as e:
        print(f"❌ Hiba a fájlok betöltésekor: {e}")
        return

    print(f"🧠 Modell betöltése a {vectorizer_device}-re...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device=vectorizer_device)

    q_vec = model.encode([query], normalize_embeddings=True)
    distances, indices = index.search(np.array(q_vec).astype('float32'), top_k)

    print("\n" + "="*80)
    print("📚 KINYERT TUDÁS (FAISS -> SQLite)")
    print("="*80)

    context_chunks = []

    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        cursor.execute("SELECT source_repo, filepath, content FROM rag_data WHERE id=?", (int(idx),))
        res = cursor.fetchone()
        if res:
            repo, path, content = res
            print(f"\n[{i+1}] REPO: {repo} | FILE: {path} | DISTANCE: {dist:.4f}")
            preview = content[:200].replace('\n', ' ') + "..." if len(content) > 200 else content.replace('\n', ' ')
            print(f"    Részlet: {preview}")
            context_chunks.append(content)

    print("\n" + "="*80)
    print("🤖 LLM SZINTÉZIS (GGUF Model a cuda:0 kártyán futna)")
    print("="*80)
    print("⚠️ LLM engine (pl. llama.cpp) még nem lett betöltve, mert várjuk a modellt.")
    print("A bemenet ez lett volna a promptban:\n")
    print(f"Kérdés: {query}")
    print("Kontextus: [A fenti 5 kinyert dokumentum tartalma összekapcsolva]")

    conn.close()

if __name__ == "__main__":
    main()
