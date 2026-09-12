import os
import json
import sqlite3
import faiss
import numpy as np
import time
import gc
import torch
import threading
import queue
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import signal
import argparse
import orjson
import itertools

# ==============================================================================
# BIZTONSÁGI / CUDA VÉDELMEK
# ==============================================================================
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ==============================================================================
# KONFIGURÁCIÓ
# ==============================================================================
# A VRAM 60%-on volt, emelhetjük a batchet, hogy a GPU többet egyen egyszerre
BATCH_SIZE = 384
MODEL_NAME = 'all-MiniLM-L6-v2'

# Queue méretek
PREFETCH_QUEUE_SIZE = 100
WRITE_QUEUE_SIZE = 200

shutdown_flag = False

def signal_handler(sig, frame):
    print("\n🛑 [PAUSE JELZÉS] Leállítási folyamat megkezdődött. Az adatok lemezre mentése...")
    global shutdown_flag
    shutdown_flag = True

def init_database(db_path):
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

def get_state(state_file):
    if os.path.exists(state_file):
        try:
            with open(state_file, 'rb') as f:
                data = orjson.loads(f.read())
                return data.get("lines_read", 0)
        except:
            pass
    return 0

def save_state(lines_read, state_file):
    with open(state_file, 'wb') as f:
        f.write(orjson.dumps({"lines_read": lines_read}))

def get_total_lines(filepath):
    meta_file = filepath + ".meta"
    if os.path.exists(meta_file):
        with open(meta_file, 'r') as f:
            return int(f.read().strip())

    print("⏳ A JSONL fájl sorainak megszámlálása (csak egyszer fut le)...")
    count = sum(1 for _ in open(filepath, 'rb'))
    with open(meta_file, 'w') as f:
        f.write(str(count))
    return count

# ==============================================================================
# WRITER THREAD (Checkpointing és SQLite WAL mentés)
# ==============================================================================
def writer_thread_worker(output_queue, db_file, index_file, state_file, dim):
    print("💾 Writer I/O Szál indítása...")
    conn, cursor = init_database(db_file)

    if os.path.exists(index_file):
        try:
            index = faiss.read_index(index_file)
        except:
            index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))
    else:
        index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))

    total_inserted = 0
    last_processed_line = 0

    while True:
        item = output_queue.get()
        if item is None:
            break

        batch_metadata, embeddings, processed_line = item

        try:
            cursor.execute("BEGIN TRANSACTION")
            start_id = None
            for row in batch_metadata:
                cursor.execute('INSERT INTO rag_data (source_repo, filepath, content) VALUES (?, ?, ?)', row)
                if start_id is None:
                    start_id = cursor.lastrowid
            conn.commit()

            last_id = cursor.lastrowid
            if start_id is not None and last_id is not None:
                db_ids = np.arange(start_id, last_id + 1).astype('int64')
                index.add_with_ids(np.array(embeddings).astype('float32'), db_ids)

            total_inserted += len(batch_metadata)
            last_processed_line = processed_line

            if total_inserted > 0 and total_inserted % (BATCH_SIZE * 400) == 0:
                faiss.write_index(index, index_file)
                save_state(last_processed_line, state_file)

        except Exception as e:
            print(f"\n❌ Hiba az adatbázis/faiss írásánál: {e}")
            conn.rollback()

    print("\n💾 [PAUSE/RESUME] Végső mentés a lemezre (Checkpoint)...")
    faiss.write_index(index, index_file)
    save_state(last_processed_line, state_file)
    conn.close()
    print("💾 Writer I/O leállt biztonságosan.")

# ==============================================================================
# PREFETCH THREAD (Aszinkron olvasó a GPU 100% etetéséhez)
# ==============================================================================
def reader_thread_worker(data_path, input_queue, skip_lines):
    print("📦 Aszinkron Előolvasó (Prefetch Thread) indítása...")
    current_line = skip_lines
    batch_texts = []
    batch_metadata = []

    try:
        with open(data_path, 'rb') as f:
            iterator = itertools.islice(f, skip_lines, None)

            for line in iterator:
                if shutdown_flag:
                    break

                current_line += 1
                try:
                    data = orjson.loads(line)
                    content = data.get("content")
                    if content:
                        batch_texts.append(content)
                        batch_metadata.append((
                            data.get("repo_name", "Unknown"),
                            data.get("filepath", "Unknown"),
                            content
                        ))
                except Exception:
                    continue

                if len(batch_texts) >= BATCH_SIZE:
                    # Megvárjuk, amíg a GPU leeszik a queue-ból
                    input_queue.put((batch_texts, batch_metadata, current_line))
                    batch_texts = []
                    batch_metadata = []

            if batch_texts and not shutdown_flag:
                input_queue.put((batch_texts, batch_metadata, current_line))

    except Exception as e:
        print(f"❌ Olvasó Hiba: {e}")

    input_queue.put(None)
    print("📦 Olvasó Szál leállt.")

# ==============================================================================
# FŐSZÁL: GPU CONSUMER (Nincs várakozás)
# ==============================================================================
def main():
    global shutdown_flag

    parser = argparse.ArgumentParser(description="Perfect Vectorizer")
    parser.add_argument("--jsonl", type=str, required=True)
    parser.add_argument("--db", type=str, required=True)
    parser.add_argument("--index", type=str, required=True)
    parser.add_argument("--state", type=str, required=True)
    args = parser.parse_args()

    JSONL_FILE = args.jsonl
    DB_FILE = args.db
    INDEX_FILE = args.index
    STATE_FILE = args.state

    print("=== 🚀 RAG PERFECT VECTORIZER (ASYNCHRONOUS PIPELINE) ===")

    device_count = torch.cuda.device_count()
    if device_count > 1:
        print(f"✅ Dual-GPU észlelve. Vektorizáló: cuda:1")
        device = 'cuda:1'
    else:
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

    print(f"🧠 Modell betöltése: {device}...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    processed_lines = get_state(STATE_FILE)
    print(f"🔍 Aktuális Checkpoint: {processed_lines} sor feldolgozva.")
    total_lines = get_total_lines(JSONL_FILE)

    if processed_lines >= total_lines:
        print("✅ Minden adat fel van dolgozva.")
        return

    # Queue-k a három komponens (Reader -> GPU -> Writer) szinkronizálására
    input_queue = queue.Queue(maxsize=PREFETCH_QUEUE_SIZE)
    output_queue = queue.Queue(maxsize=WRITE_QUEUE_SIZE)

    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension() if hasattr(model, 'get_sentence_embedding_dimension') else model.get_embedding_dimension()

    # Háttér szálak indítása
    writer_thread = threading.Thread(target=writer_thread_worker, args=(output_queue, DB_FILE, INDEX_FILE, STATE_FILE, dim))
    writer_thread.daemon = True
    writer_thread.start()

    reader_thread = threading.Thread(target=reader_thread_worker, args=(JSONL_FILE, input_queue, processed_lines))
    reader_thread.daemon = True
    reader_thread.start()

    start_time = time.time()
    print("🚀 GPU Encode Ciklus Indulése... (Nyomj Ctrl+C a biztonságos Pause-hoz!)")

    pbar = tqdm(total=total_lines - processed_lines, desc="Vektorizálás", unit="sor")

    try:
        while not shutdown_flag:
            item = input_queue.get()
            if item is None:
                break

            batch_texts, batch_metadata, current_line = item

            # TISZTA GPU MÁTRIXSZORZÁS (A CPU nem blokkolja, mert háttérszál olvassa)
            embeddings = model.encode(batch_texts, batch_size=BATCH_SIZE, show_progress_bar=False, normalize_embeddings=True)
            output_queue.put((batch_metadata, embeddings, current_line))

            pbar.update(len(batch_texts))

            if 'cuda' in device:
                torch.cuda.empty_cache()

    except KeyboardInterrupt:
        print("\n⚠️ Felhasználói megszakítás.")
    finally:
        shutdown_flag = True
        pbar.close()

    print("\n🛑 Rendszer leállítása, folyamatok bevárása...")

    # Reader queue feloldása, ha blokkolt
    try:
        while not input_queue.empty():
            input_queue.get_nowait()
    except:
        pass

    output_queue.put(None)
    writer_thread.join()
    reader_thread.join()

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"⏱️ Futási idő: {elapsed/60:.2f} perc.")

if __name__ == "__main__":
    main()
