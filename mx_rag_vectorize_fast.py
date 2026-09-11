import os
import json
import sqlite3
import faiss
import numpy as np
import time
import gc
import torch
import multiprocessing as mp
import threading
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# ==============================================================================
# BIZTONSÁGI / CUDA VÉDELMEK
# ==============================================================================
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    mp.set_start_method('spawn')
except RuntimeError:
    pass

# ==============================================================================
# KONFIGURÁCIÓ A QUADRO P2000-HEZ ÉS XEON E5-1620 (8 MAG, 32GB RAM)
# ==============================================================================
WORK_DIR = "/home/Jules/MX_LINUX_RAG"
JSONL_FILE = os.path.join(WORK_DIR, "mxlinux_dev.jsonl")
DB_FILE = os.path.join(WORK_DIR, "mxlinux_dev_metadata.db")
INDEX_FILE = os.path.join(WORK_DIR, "mxlinux_dev_index.faiss")

# Optimális 5GB VRAM-ra (65% usage)
BATCH_SIZE = 256
MODEL_NAME = 'all-MiniLM-L6-v2'

# Queue méretek (Brutálisan megemelve a CPU tüskék és a GPU starvation ellen)
PREFETCH_QUEUE_SIZE = 200
WRITE_QUEUE_SIZE = 200

# 6 szál fogja olvasni és json.load() dekódolni a nyers adatot!
NUM_PRODUCERS = 6

def init_database(db_path):
    """Létrehozza vagy BETÖLTI a strukturált SQLite adatbázist a folytatáshoz."""
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
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

def get_processed_count(db_path):
    """Lekérdezi, hány rekord van már az adatbázisban a folytatáshoz."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM rag_data")
        count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        count = 0
    conn.close()
    return count

def count_total_lines(filepath):
    print("⏳ A JSONL fájl sorainak gyors megszámlálása...")
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for _ in f:
            count += 1
    return count

def init_faiss(faiss_path, dim):
    if os.path.exists(faiss_path):
        print(f"🗄️ FAISS Index betöltése: {faiss_path}")
        return faiss.read_index(faiss_path)
    print("🗄️ Új FAISS Index inicializálása (CPU/RAM)...")
    return faiss.IndexIDMap(faiss.IndexFlatL2(dim))

# ==============================================================================
# PRODUCER WORKER - MULTIPROCESSING
# 6 db fut egyszerre! Szétosztják maguk között a fájl sorait modulo alapon.
# ==============================================================================
def producer_worker(worker_id, num_workers, data_path, input_queue, skip_lines, total_lines):
    print(f"📦 Producer-{worker_id} indítása... Átugorva: {skip_lines} rekord.")
    batch_texts = []
    batch_metadata = []
    current_line = 0

    with open(data_path, 'r', encoding='utf-8') as f:
        iterator = tqdm(f, total=total_lines, desc=f"🔄 Beolvasás", initial=skip_lines) if worker_id == 0 else f
        for line in iterator:
            # Gyors átugrás a checkpointig
            if current_line < skip_lines:
                current_line += 1
                continue

            # Modulo szétosztás a worker-ek között (nincs ütközés)
            if current_line % num_workers != worker_id:
                current_line += 1
                continue
            current_line += 1

            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                repo_name = data.get("metadata", {}).get("repo", "Unknown")
                filepath = data.get("metadata", {}).get("file_path", "Unknown")
                content = data.get("text", "")

                if content:
                    batch_texts.append(content)
                    batch_metadata.append((repo_name, filepath, content))
            except json.JSONDecodeError:
                continue

            if len(batch_texts) >= BATCH_SIZE:
                # Blokkol a queue.put ha tele van, megvédve a RAM-ot
                input_queue.put((batch_texts, batch_metadata))
                batch_texts = []
                batch_metadata = []

        # Maradék batchek elküldése
        if batch_texts:
            input_queue.put((batch_texts, batch_metadata))

    # EOF jelző - minden worker dob egy None-t
    input_queue.put(None)
    print(f"\n📦 Producer-{worker_id} beolvasás befejezve.")

# ==============================================================================
# WRITER THREAD (DB & Faiss I/O)
# ==============================================================================
def writer_thread_worker(output_queue, db_file, index_file, dim):
    print("💾 Writer I/O Szál indítása...")
    conn, cursor = init_database(db_file)

    if os.path.exists(index_file):
        print(f"🗄️ FAISS Index betöltése a folytatáshoz: {index_file}")
        index = faiss.read_index(index_file)
    else:
        index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))

    total_inserted = 0

    while True:
        item = output_queue.get()
        if item is None:
            output_queue.task_done()
            break

        batch_metadata, embeddings = item

        try:
            cursor.execute("BEGIN TRANSACTION")
            cursor.executemany('INSERT INTO rag_data (source_repo, filepath, content) VALUES (?, ?, ?)', batch_metadata)
            conn.commit()

            last_id = cursor.lastrowid
            start_id = last_id - len(batch_metadata) + 1
            db_ids = np.arange(start_id, last_id + 1).astype('int64')

            index.add_with_ids(np.array(embeddings).astype('float32'), db_ids)
            total_inserted += len(batch_metadata)

            # 5 GPU kötegenként írjuk a Faisst (256 * 5)
            if total_inserted % (BATCH_SIZE * 5) == 0:
                faiss.write_index(index, index_file)

        except Exception as e:
            print(f"\n❌ Hiba az adatbázis/faiss írásánál: {e}")
            conn.rollback()
        finally:
            output_queue.task_done()

    print("\n💾 Végső mentés a lemezre...")
    faiss.write_index(index, index_file)
    conn.close()
    print("💾 Writer I/O leállt.")

# ==============================================================================
# FŐSZÁL: GPU CONSUMER
# Kizárólag a modellt futtatja. Nincs I/O, nincs JSON parse. Max GPU throughput.
# ==============================================================================
def main():
    print("=== 🚀 RAG ULTRA-GPU VECTORIZER (6 PRODUCER - 1 CONSUMER) ===")
    if not os.path.exists(JSONL_FILE):
        print(f"❌ HIBA: Nem található a {JSONL_FILE} fájl!")
        return

    processed_count = get_processed_count(DB_FILE)
    print(f"🔍 Aktuális Checkpoint: {processed_count} rekord van már az adatbázisban.")
    total_lines = count_total_lines(JSONL_FILE)

    if processed_count >= total_lines:
        print("✅ Minden adat fel van dolgozva.")
        return

    # Mivel sok szál termel, dupla buffer kell a gyorsasághoz
    input_queue = mp.Queue(maxsize=PREFETCH_QUEUE_SIZE)
    import queue
    output_queue = queue.Queue(maxsize=WRITE_QUEUE_SIZE)

    producers = []
    for i in range(NUM_PRODUCERS):
        p = mp.Process(target=producer_worker, args=(i, NUM_PRODUCERS, JSONL_FILE, input_queue, processed_count, total_lines))
        producers.append(p)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🧠 Modell betöltése GPU-ra ({device})...")
    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension() if hasattr(model, 'get_sentence_embedding_dimension') else model.get_embedding_dimension()

    writer_thread = threading.Thread(target=writer_thread_worker, args=(output_queue, DB_FILE, INDEX_FILE, dim))
    writer_thread.daemon = True
    writer_thread.start()

    start_time = time.time()
    print("🚀 GPU Encode Ciklus Indulése... Készen áll a mátrixszorzásra!")

    for p in producers:
        p.start()

    finished_producers = 0
    try:
        while True:
            # Itt már azonnal kapja a JSONL-t a memóriából a 6 szál jóvoltából!
            item = input_queue.get()
            if item is None:
                finished_producers += 1
                if finished_producers == NUM_PRODUCERS:
                    break
                continue

            batch_texts, batch_metadata = item

            # TISZTA GPU MÁTRIXSZORZÁS
            embeddings = model.encode(batch_texts, batch_size=BATCH_SIZE, show_progress_bar=False, normalize_embeddings=True)

            # Átadjuk az aszinkron írónak
            output_queue.put((batch_metadata, embeddings))

            if device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()

    except KeyboardInterrupt:
        print("\n⚠️ A felhasználó megszakította a folyamatot (Ctrl+C). A Writer befejezi a hátralévő mentéseket...")

    output_queue.put(None)
    writer_thread.join()
    for p in producers:
        p.join()

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"⏱️ Futási idő: {elapsed/60:.2f} perc.")

if __name__ == "__main__":
    main()
