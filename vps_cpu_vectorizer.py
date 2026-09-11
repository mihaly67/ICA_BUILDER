import os
import sqlite3
import faiss
import torch
import gc
from sentence_transformers import SentenceTransformer

# --- KONFIGURÁCIÓ ---
# Kényszerítjük a PyTorch-ot, hogy használja ki a 8 Ryzen magot
torch.set_num_threads(8)

REPO_PATH = "/home/misi/RAG_epito_ismeretek"
DB_PATH = "metadata.db"
FAISS_PATH = "vectors.index"
BATCH_SIZE = 50
MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_DIM = 384

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            faiss_id INTEGER PRIMARY KEY,
            repo TEXT,
            filepath TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

def main():
    print("[INIT] Adatbázis és modell betöltése (CPU mód)...")
    conn, cursor = init_db()

    model = SentenceTransformer(MODEL_NAME, device='cpu')
    index = faiss.IndexFlatL2(EMBEDDING_DIM)

    batch_texts = []
    batch_meta = []
    total_processed = 0

    def process_batch():
        nonlocal batch_texts, batch_meta, total_processed
        if not batch_texts:
            return

        print(f"[FELDOLGOZÁS] Vektorizálás ({len(batch_texts)} db chunk)...", flush=True)
        embeddings = model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=False)

        start_id = index.ntotal
        index.add(embeddings)

        db_data = []
        for i, meta in enumerate(batch_meta):
            db_data.append((start_id + i, meta['repo'], meta['filepath'], meta['code']))

        cursor.executemany(
            "INSERT INTO chunks (faiss_id, repo, filepath, content) VALUES (?, ?, ?, ?)",
            db_data
        )
        conn.commit()

        total_processed += len(batch_texts)
        print(f"[MENTVE] Összesen indexelve: {total_processed} rekord.", flush=True)

        batch_texts.clear()
        batch_meta.clear()
        gc.collect()

    print("[START] Fájlok beolvasása...")
    for root, dirs, files in os.walk(REPO_PATH):
        if '.git' in root or 'node_modules' in root or '__pycache__' in root or 'venv' in root:
            continue
        for file in files:
            if file.endswith(('.py', '.js', '.md', '.cpp', '.ts', '.html', '.css', '.txt')):
                file_path = os.path.join(root, file)
                try:
                    # MAX 100KB méret, felette egyből kihagyjuk OOM esélye miatt
                    if os.path.getsize(file_path) > 100000:
                        continue
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                        if not content.strip():
                            continue

                        chunks = [content[i:i+500] for i in range(0, len(content), 500)]
                        rel_path = os.path.relpath(root, REPO_PATH)
                        repo_name = rel_path.split(os.sep)[0] if rel_path != '.' else "root"

                        for chunk in chunks:
                            batch_texts.append(chunk)
                            batch_meta.append({
                                "repo": repo_name,
                                "filepath": file_path,
                                "code": chunk
                            })

                            if len(batch_texts) >= BATCH_SIZE:
                                process_batch()
                except Exception as e:
                    continue

    process_batch()
    faiss.write_index(index, FAISS_PATH)
    conn.close()
    print(f"[KÉSZ] A vektorizálás befejeződött. Kész fájlok: {FAISS_PATH} és {DB_PATH}")

if __name__ == '__main__':
    main()
