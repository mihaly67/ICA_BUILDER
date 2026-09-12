import os
import sqlite3
import faiss
import numpy as np
import torch
import sys
import gc
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# ==============================================================================
# KONFIGURÁCIÓ ÉS ÚTVONALAK
# ==============================================================================
WORK_DIR = "/home/Jules/RAG_epito_ismeretek"
DB_FILE = os.path.join(WORK_DIR, "rag_knowledge.db")
INDEX_FILE = os.path.join(WORK_DIR, "rag_vectors.index")

# Vektorizáló modell
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

# Mini AI modell kontextus szintetizáláshoz (TinyLlama gyors, kisméretű)
LLM_MODEL_NAME = 'TinyLlama/TinyLlama-1.1B-Chat-v1.0'

def main():
    if len(sys.argv) < 2:
        query = "how to optimize fast vectorization python for large jsonl dataset chunking I/O bottleneck multiprocessing"
    else:
        query = " ".join(sys.argv[1:])

    top_k = 5

    print(f"=== 🧠 AI TÁMOGATÁSÚ RAG KERESŐ (CUDA AKTÍV) ===")
    print(f"🔍 Lekérdezés: '{query}'")

    # 1. Adatbázisok betöltése
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        index = faiss.read_index(INDEX_FILE)
        print("✅ FAISS és SQLite adatbázisok betöltve.")
    except Exception as e:
        print(f"❌ Hiba a fájlok betöltésekor: {e}")
        return

    # 2. Embedding Modell betöltése
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🚀 Embedding Modell betöltése: {EMBEDDING_MODEL_NAME} ({device})")
    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)

    # 3. Szemantikus Keresés
    print("🔍 FAISS keresés folyamatban...")
    q_vec = embed_model.encode([query], normalize_embeddings=True)
    distances, indices = index.search(np.array(q_vec).astype('float32'), top_k)

    context_chunks = []
    print("\n" + "="*80)
    print("📚 KINYERT TUDÁS (FAISS)")
    print("="*80)

    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        cursor.execute("SELECT source_repo, filepath, content FROM rag_data WHERE id=?", (int(idx),))
        res = cursor.fetchone()
        if res:
            repo, path, content = res
            print(f"\n[{i+1}] REPO: {repo} | FILE: {path} | TÁVOLSÁG: {dist:.4f}")
            preview = content[:150].replace('\n', ' ') + "..." if len(content) > 150 else content.replace('\n', ' ')
            print(f"    Részlet: {preview}")
            context_chunks.append(f"Repo: {repo}, File: {path}\nContent:\n{content}")

    conn.close()

    # VRAM Felszabadítása a LLM számára (Fontos a Quadro P2000-es 5GB limittel!)
    del embed_model
    del q_vec
    del distances
    del indices
    del index
    if device == 'cuda':
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

    # 4. LLM Szintézis (Mini AI betöltése)
    print("\n" + "="*80)
    print(f"🤖 LLM SZINTÉZIS BETÖLTÉSE: {LLM_MODEL_NAME} ({device})")
    print("="*80)

    try:
        tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_NAME,
            torch_dtype=torch.float16 if device == 'cuda' else torch.float32,
            low_cpu_mem_usage=True
        ).to(device)

        generator = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device=0 if device == 'cuda' else -1,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.2,
            truncation=True
        )
        print("✅ Mini LLM sikeresen betöltve a memóriába.")
    except Exception as e:
        print(f"❌ Hiba a Mini LLM betöltésekor: {e}")
        return

    # Összevont kontextus készítése
    context_str = "\n\n".join(context_chunks)

    prompt = f"""<|system|>
You are an advanced software architect AI. You analyze code context and provide structural plans, patterns, and deep insights. Focus on python code for large jsonl dataset chunking I/O bottleneck multiprocessing. Respond in Hungarian.</s>
<|user|>
Context from the codebase:
{context_str}

Query: {query}
Please analyze the above context, find patterns, and provide a detailed plan/proposal to solve the problem based on the provided RAG knowledge! Focus on python code for large jsonl dataset chunking I/O bottleneck multiprocessing. Respond in Hungarian.</s>
<|assistant|>
"""

    print("\n🧠 AI Válaszadás (CUDA generálás folyamatban)...\n")

    result = generator(prompt, num_return_sequences=1)
    generated_text = result[0]['generated_text']

    # A prompt eltávolítása a válaszból
    assistant_marker = "<|assistant|>"
    if assistant_marker in generated_text:
        final_response = generated_text.split(assistant_marker)[-1].strip()
    else:
        final_response = generated_text.strip()

    print(final_response)
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
