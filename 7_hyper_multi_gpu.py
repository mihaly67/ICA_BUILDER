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
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import queue
import signal
import argparse
import psutil

# ==============================================================================
# BIZTONSÁGI / CUDA VÉDELMEK
# ==============================================================================
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    mp.set_start_method('spawn')
except RuntimeError:
    pass

# ==============================================================================
# KONFIGURÁCIÓ
# ==============================================================================
BATCH_SIZE = 256
MODEL_NAME = 'all-MiniLM-L6-v2'

PREFETCH_QUEUE_SIZE = 200
WRITE_QUEUE_SIZE = 200
NUM_WORKERS = 6

shutdown_flag = False

def signal_handler(sig, frame):
    print("\n🛑 [PAUSE JELZÉS] Leállítási folyamat megkezdődött. Az adatok lemezre mentése...")
    global shutdown_flag
    shutdown_flag = True

def kill_zombie_processes():
    import subprocess
    try:
        # A felhasználó kifejezett kérésére a rendszerbe ragadt multiprocessing zombie-kat lőjük ki, amik 100% ramot esznek
        subprocess.run(["pkill", "-9", "-f", "multiprocessing.spawn"], stderr=subprocess.DEVNULL)
    except Exception:
        pass

def clear_linux_page_cache():
    import subprocess
    try:
        subprocess.run(["sudo", "-n", "sh", "-c", "echo 1 > /proc/sys/vm/drop_caches"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

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
            with open(state_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"workers": {str(i): 0 for i in range(NUM_WORKERS)}}

def save_state(state, state_file):
    with open(state_file, 'w') as f:
        json.dump(state, f)

# ==============================================================================
# BYTE CHUNKING OLVASÓ PROCESSZ
# ==============================================================================
def reader_process(worker_id, data_path, start_byte, end_byte, input_queue, start_offset, shutdown_event):
    print(f"📦 Olvasó Processz [{worker_id}] indítása (Tartomány: {start_byte} - {end_byte} bytes)...")

    batch_texts = []
    batch_metadata = []
    current_pos = start_byte + start_offset

    try:
        # rb (binary) mód kötelező a seek() hiba és a UnicodeEncodeError megelőzése végett!
        with open(data_path, 'rb') as f:
            f.seek(current_pos)

            # Ha nem a fájl legelején vagyunk, el kell mennünk az első újsorig, hogy ne vágjuk ketté a UTF-8 JSON sort
            if current_pos != 0 and start_offset == 0:
                f.readline()
                current_pos = f.tell()

            for line in f:
                if shutdown_event.is_set() or current_pos >= end_byte:
                    break

                line_length = len(line)
                current_pos += line_length

                try:
                    line = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    continue

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
                    mem = psutil.virtual_memory()
                    if mem.available / mem.total < 0.15:
                        time.sleep(1)

                    while not shutdown_event.is_set():
                        try:
                            processed_bytes = current_pos - start_byte
                            input_queue.put((batch_texts, batch_metadata, worker_id, processed_bytes), timeout=1)
                            batch_texts = []
                            batch_metadata = []
                            break
                        except queue.Full:
                            continue

            if batch_texts and not shutdown_event.is_set():
                while not shutdown_event.is_set():
                    try:
                        processed_bytes = current_pos - start_byte
                        input_queue.put((batch_texts, batch_metadata, worker_id, processed_bytes), timeout=1)
                        break
                    except queue.Full:
                        continue

    except Exception as e:
        print(f"❌ Olvasó Hiba [{worker_id}]: {e}")

    input_queue.put(None)  # EOF
    print(f"📦 Olvasó [{worker_id}] befejezte a munkát.")

# ==============================================================================
# WRITER THREAD (Checkpointing és SQLite WAL mentés)
# ==============================================================================
def writer_thread_worker(output_queue, db_file, index_file, state_file, dim, shutdown_event, state):
    print("💾 Writer I/O Szál indítása...")
    conn, cursor = init_database(db_file)

    if os.path.exists(index_file):
        index = faiss.read_index(index_file)
    else:
        index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))

    total_inserted = 0

    while True:
        item = output_queue.get()
        if item is None:
            break

        batch_metadata, embeddings, worker_id, processed_bytes = item

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
            state["workers"][str(worker_id)] = processed_bytes

            if total_inserted > 0 and total_inserted % (BATCH_SIZE * 400) == 0:
                faiss.write_index(index, index_file)
                save_state(state, state_file)
                clear_linux_page_cache()

        except Exception as e:
            print(f"\n❌ Hiba az adatbázis/faiss írásánál: {e}")
            conn.rollback()

    print("\n💾 [PAUSE/RESUME] Végső mentés a lemezre (Checkpoint)...")
    faiss.write_index(index, index_file)
    save_state(state, state_file)
    conn.close()
    print("💾 Writer I/O leállt biztonságosan.")

# ==============================================================================
# FŐSZÁL: KÖVETKEZŐ GENERÁCIÓS MULTI-WORKER GPU CONSUMER
# ==============================================================================
def main():
    global shutdown_flag
    kill_zombie_processes()

    parser = argparse.ArgumentParser(description="Multi-Worker Hyper Vectorizer")
    parser.add_argument("--jsonl", type=str, required=True, help="Input JSONL file")
    parser.add_argument("--db", type=str, required=True, help="Output SQLite DB file")
    parser.add_argument("--index", type=str, required=True, help="Output FAISS index file")
    parser.add_argument("--state", type=str, required=True, help="Output state JSON file")
    args = parser.parse_args()

    JSONL_FILE = args.jsonl
    DB_FILE = args.db
    INDEX_FILE = args.index
    STATE_FILE = args.state

    print("=== 🚀 RAG MULTI-WORKER HYPER VECTORIZER ===")

    device_count = torch.cuda.device_count()
    if device_count > 1:
        print(f"✅ Dual-GPU észlelve ({device_count} kártya). Vektorizáló az 1. GPU-ra (cuda:1) irányítva.")
        device = 'cuda:1'
    else:
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

    print(f"🧠 Modell betöltése: {device}...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    shutdown_event = mp.Event()

    state = get_state(STATE_FILE)
    file_size = os.path.getsize(JSONL_FILE)
    chunk_size = file_size // NUM_WORKERS

    input_queue = mp.Queue(maxsize=PREFETCH_QUEUE_SIZE)
    output_queue = queue.Queue(maxsize=WRITE_QUEUE_SIZE)

    workers = []
    for i in range(NUM_WORKERS):
        start_byte = i * chunk_size
        end_byte = file_size if i == NUM_WORKERS - 1 else (i + 1) * chunk_size

        worker_offset = state["workers"].get(str(i), 0)

        if start_byte + worker_offset >= end_byte:
            continue

        p = mp.Process(target=reader_process, args=(i, JSONL_FILE, start_byte, end_byte, input_queue, worker_offset, shutdown_event))
        workers.append(p)
        p.start()

    if not workers:
        print("✅ Minden adat fel van dolgozva.")
        return

    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension() if hasattr(model, 'get_sentence_embedding_dimension') else model.get_embedding_dimension()

    writer_thread = threading.Thread(target=writer_thread_worker, args=(output_queue, DB_FILE, INDEX_FILE, STATE_FILE, dim, shutdown_event, state))
    writer_thread.daemon = True
    writer_thread.start()

    start_time = time.time()
    print("🚀 GPU Encode Ciklus Indulése... (Nyomj Ctrl+C a biztonságos Pause-hoz!)")

    estimated_total_batches = (file_size // (2000)) // BATCH_SIZE
    pbar = tqdm(total=estimated_total_batches, desc="Batchek feldolgozása")

    finished_workers = 0
    try:
        while not shutdown_flag:
            try:
                item = input_queue.get(timeout=1)
            except queue.Empty:
                if finished_workers == len(workers):
                    break
                continue

            if item is None:
                finished_workers += 1
                continue

            batch_texts, batch_metadata, worker_id, processed_bytes = item

            embeddings = model.encode(batch_texts, batch_size=BATCH_SIZE, show_progress_bar=False, normalize_embeddings=True)
            output_queue.put((batch_metadata, embeddings, worker_id, processed_bytes))

            pbar.update(1)

            if 'cuda' in device:
                torch.cuda.empty_cache()
            gc.collect()

    except KeyboardInterrupt:
        print("\n⚠️ Felhasználói megszakítás.")
    finally:
        shutdown_flag = True
        shutdown_event.set()
        pbar.close()

    print("\n🛑 Rendszer leállítása, folyamatok bevárása...")

    try:
        while not input_queue.empty():
            input_queue.get_nowait()
    except:
        pass

    output_queue.put(None)
    writer_thread.join()
    for w in workers:
        w.join()

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"⏱️ Futási idő: {elapsed/60:.2f} perc.")

if __name__ == "__main__":
    main()
