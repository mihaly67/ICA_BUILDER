import os
import json
import sqlite3
import faiss
import numpy as np
import time
import gc
import torch
from tqdm import tqdm
import multiprocessing as mp
from sentence_transformers import SentenceTransformer

# ==============================================================================
# BIZTONSÁGI / CUDA VÉDELMEK
# ==============================================================================
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Szigorú Multiprocessing beállítás Linuxra a CUDA miatt
try:
    mp.set_start_method('spawn')
except RuntimeError:
    pass

# ==============================================================================
# KONFIGURÁCIÓ A QUADRO P2000-HEZ (5GB VRAM) & XEON E5-1620 v3 CPU-hoz
# ==============================================================================
WORK_DIR = "/home/Jules/RAG_epito_ismeretek"
JSONL_FILE = os.path.join(WORK_DIR, "dataset.jsonl")
DB_FILE = os.path.join(WORK_DIR, "rag_knowledge.db")
INDEX_FILE = os.path.join(WORK_DIR, "rag_vectors.index")

# Növelt batch méret a gyorsabb GPU kihasználtságért.
BATCH_SIZE = 256
MODEL_NAME = 'all-MiniLM-L6-v2'
PREFETCH_QUEUE_SIZE = 50

def init_database(db_path):
    """Létrehozza vagy BETÖLTI a strukturált SQLite adatbázist a folytatáshoz."""
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL;")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rag_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_repo TEXT,
            filepath TEXT,
            content TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_repo ON rag_data (source_repo)')
    conn.commit()
    return conn, cursor

def get_processed_count(cursor):
    """Lekérdezi, hány rekord van már az adatbázisban a folytatáshoz."""
    cursor.execute("SELECT COUNT(*) FROM rag_data")
    return cursor.fetchone()[0]

def count_total_lines(filepath):
    """Gyors előzetes sor számlálás a tqdm számára."""
    print("⏳ A JSONL fájl sorainak gyors megszámlálása...")
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for _ in f:
            count += 1
    return count

def init_faiss(faiss_path, dim):
    """Létrehozza vagy BETÖLTI a Faiss indexet a folytatáshoz."""
    if os.path.exists(faiss_path):
        print(f"🗄️ FAISS Index betöltése: {faiss_path}")
        return faiss.read_index(faiss_path)
    print("🗄️ Új FAISS Index inicializálása (CPU/RAM)...")
    return faiss.IndexIDMap(faiss.IndexFlatL2(dim))

def producer_worker(worker_id, num_workers, data_path, input_queue, skip_lines, total_lines):
    print(f"📦 Producer-{worker_id} indítása... Átugorva: {skip_lines} rekord.")
    batch_texts = []
    batch_metadata = []
    current_line = 0

    with open(data_path, 'r', encoding='utf-8') as f:
        iterator = tqdm(f, total=total_lines, desc=f"🔄 Beolvasás", initial=skip_lines) if worker_id == 0 else f
        for line in iterator:
            if current_line < skip_lines:
                current_line += 1
                continue

            if current_line % num_workers != worker_id:
                current_line += 1
                continue
            current_line += 1

            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                repo_name = data.get("repo_name", "Unknown")
                filepath = data.get("filepath", "Unknown")
                content = data.get("content", "")

                if content:
                    batch_texts.append(content)
                    batch_metadata.append((repo_name, filepath, content))
            except json.JSONDecodeError:
                continue

            if len(batch_texts) >= BATCH_SIZE:
                input_queue.put((batch_texts, batch_metadata))
                batch_texts = []
                batch_metadata = []

        if batch_texts:
            input_queue.put((batch_texts, batch_metadata))

    input_queue.put(None)
    print(f"\n📦 Producer-{worker_id} beolvasás befejezve.")

def consumer_worker(input_queue, db_file, index_file, num_producers):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🧠 Modell betöltése GPU-ra ({device})...")
    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension() if hasattr(model, 'get_sentence_embedding_dimension') else model.get_embedding_dimension()

    conn, cursor = init_database(db_file)
    index = init_faiss(index_file, dim)

    print("🚀 GPU Consumer folyamat indítása...")
    total_inserted = 0
    finished_producers = 0

    while True:
        item = input_queue.get()
        if item is None:
            finished_producers += 1
            if finished_producers == num_producers:
                break
            continue

        batch_texts, batch_metadata = item

        try:
            cursor.execute("BEGIN TRANSACTION")
            cursor.executemany('INSERT INTO rag_data (source_repo, filepath, content) VALUES (?, ?, ?)', batch_metadata)
            conn.commit()

            last_id = cursor.lastrowid
            start_id = last_id - len(batch_metadata) + 1
            db_ids = np.arange(start_id, last_id + 1).astype('int64')

            embeddings = model.encode(batch_texts, batch_size=BATCH_SIZE, show_progress_bar=False, normalize_embeddings=True)

            index.add_with_ids(np.array(embeddings).astype('float32'), db_ids)

            total_inserted += len(batch_texts)

            if total_inserted % (BATCH_SIZE * 4) == 0:
                faiss.write_index(index, index_file)

        except Exception as e:
            print(f"\n❌ Hiba a vektorizálásnál: {e}")
            conn.rollback()
        finally:
            if device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()

    print("\n💾 Végső mentés...")
    faiss.write_index(index, index_file)
    conn.close()
    print(f"✅ KÜLDETÉS TELJESÍTVE! GPU Consumer leállt. Összesen feldolgozva ebben a körben: {total_inserted}")

def main():
    print("=== 🚀 RAG MULTI-PRODUCER VECTORIZER (MAX CPU/GPU) ===")
    if not os.path.exists(JSONL_FILE):
        print(f"❌ HIBA: Nem található a {JSONL_FILE} fájl!")
        return

    conn, cursor = init_database(DB_FILE)
    processed_count = get_processed_count(cursor)
    conn.close()

    print(f"🔍 Aktuális állapot: {processed_count} rekord van már az adatbázisban.")
    total_lines = count_total_lines(JSONL_FILE)

    if processed_count >= total_lines:
        print("✅ Minden adat fel van dolgozva.")
        return

    input_queue = mp.Queue(maxsize=PREFETCH_QUEUE_SIZE)

    NUM_PRODUCERS = 2
    producers = []

    for i in range(NUM_PRODUCERS):
        p = mp.Process(target=producer_worker, args=(i, NUM_PRODUCERS, JSONL_FILE, input_queue, processed_count, total_lines))
        producers.append(p)

    consumer = mp.Process(target=consumer_worker, args=(input_queue, DB_FILE, INDEX_FILE, NUM_PRODUCERS))

    start_time = time.time()

    for p in producers:
        p.start()
    consumer.start()

    for p in producers:
        p.join()
    consumer.join()

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"⏱️ Futási idő: {elapsed/60:.2f} perc.")

if __name__ == "__main__":
    main()
