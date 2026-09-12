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
import signal
import psutil
import subprocess


# ==============================================================================
# BIZTONSÁGI / CUDA VÉDELMEK
# ==============================================================================
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    mp.set_start_method('spawn')
except RuntimeError:
    pass

# ==============================================================================
# KONFIGURÁCIÓ A DUAL-GPU / HATÉKONY MULTIPROCESSING RENDSZERHEZ
# ==============================================================================
WORK_DIR = "/home/Jules/MX_LINUX_RAG"
JSONL_FILE = os.path.join(WORK_DIR, "mxlinux.jsonl")
DB_FILE = os.path.join(WORK_DIR, "mxlinux.db")
INDEX_FILE = os.path.join(WORK_DIR, "mxlinux.index")
STATE_FILE = os.path.join(WORK_DIR, "mxlinux_state.json")

# Batch Size optimalizáció (a VRAM fügvényében)
BATCH_SIZE = 256
MODEL_NAME = 'all-MiniLM-L6-v2'

# Queue méretek
PREFETCH_QUEUE_SIZE = 50
WRITE_QUEUE_SIZE = 100

# Globális leállítási jelzők
shutdown_flag = False

def signal_handler(sig, frame):
    print("\n🛑 [PAUSE JELZÉS] Leállítási folyamat megkezdődött. Az adatok lemezre mentése...")
    global shutdown_flag
    shutdown_flag = True


def kill_zombie_processes():
    print("🧹 [RAM VÉDELEM] Előző futásból beragadt zombi processzek takarítása...")
    try:
        # A multiprocessing.spawn zombik kilövése
        subprocess.run(["pkill", "-9", "-f", "multiprocessing.spawn"], stderr=subprocess.DEVNULL)
    except Exception:
        pass

def clear_linux_page_cache():
    # Megpróbálja kiüríteni a linux cache-t (jelszómentes sudo szükséges hozzá a gépen)
    try:
        subprocess.run(["sudo", "-n", "sysctl", "-w", "vm.drop_caches=1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

def get_processed_lines_state():
    """Pontos JSONL line tracker fájl betöltése, hogy ne függjön az SQLite ID-ktől (üres sorok miatt)"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get("lines_read", 0)
        except:
            pass
    return 0

def save_processed_lines_state(lines_read):
    with open(STATE_FILE, 'w') as f:
        json.dump({"lines_read": lines_read}, f)

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
# OPTIMALIZÁLT OLVASÓ (A RAG AI Javaslata alapján - Block Based Iterator)
# ==============================================================================
def reader_process(data_path, input_queue, skip_lines, shutdown_event):
    import itertools
    print(f"📦 Olvasó Processz indítása... Gyors átugrás: {skip_lines} sor.")

    batch_texts = []
    batch_metadata = []
    lines_read_this_session = 0

    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            # Villámgyors ugrás iterátor szinten (C implemetáció)
            iterator = itertools.islice(f, skip_lines, None)

            for line in iterator:
                if shutdown_event.is_set():
                    break

                # [RAM VÉDELEM] Ha a szabad RAM 15% alá esik, az olvasó várakozik
                if lines_read_this_session % 50000 == 0:
                    mem = psutil.virtual_memory()
                    if mem.available / mem.total < 0.15:
                        print(f"\n⚠️ [RAM FIGYELMEZTETÉS] Szabad RAM kritikus szinten ({(mem.available/mem.total)*100:.1f}%). Olvasó szüneteltetése 5 másodpercre...")
                        time.sleep(5)
                        gc.collect()
                        clear_linux_page_cache()

                lines_read_this_session += 1
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
                    input_queue.put((batch_texts, batch_metadata, skip_lines + lines_read_this_session))
                    batch_texts = []
                    batch_metadata = []

            # Maradék
            if batch_texts and not shutdown_event.is_set():
                input_queue.put((batch_texts, batch_metadata, skip_lines + lines_read_this_session))

    except Exception as e:
        print(f"❌ Olvasó Hiba: {e}")

    input_queue.put(None)  # EOF
    print("📦 Olvasó befejezte a munkát.")

# ==============================================================================
# WRITER THREAD (Checkpointing és SQLite WAL mentés)
# ==============================================================================
def writer_thread_worker(output_queue, db_file, index_file, dim, shutdown_event):
    print("💾 Writer I/O Szál indítása...")
    conn, cursor = init_database(db_file)

    if os.path.exists(index_file):
        print(f"🗄️ FAISS Index betöltése a folytatáshoz: {index_file}")
        index = faiss.read_index(index_file)
    else:
        index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))

    total_inserted = 0
    last_processed_line = 0

    while True:
        item = output_queue.get()
        if item is None: # Szabályos leállás vagy Pause
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

            # Biztonsági mentés (csak minden 100,000. sornál a hatalmas I/O elkerüléséért)
            if total_inserted > 0 and total_inserted % (BATCH_SIZE * 400) == 0:
                faiss.write_index(index, index_file)
                save_processed_lines_state(last_processed_line)

        except Exception as e:
            print(f"\n❌ Hiba az adatbázis/faiss írásánál: {e}")
            conn.rollback()

    print("\n💾 [PAUSE/RESUME] Végső mentés a lemezre (Checkpoint)...")
    faiss.write_index(index, index_file)
    save_processed_lines_state(last_processed_line)
    conn.close()
    print("💾 Writer I/O leállt biztonságosan.")

# ==============================================================================
# FŐSZÁL: KÖVETKEZŐ GENERÁCIÓS GPU CONSUMER (Dual-GPU Felkészített)
# ==============================================================================
def main():
    global shutdown_flag
    kill_zombie_processes()
    print("=== 🚀 RAG HYPER-VECTORIZER (AI OPTIMALIZÁLT ARCHITEKTÚRA) ===")

    # Felkészülés a Dual GPU-ra (Ha bekerül a P4000)
    device_count = torch.cuda.device_count()
    if device_count > 1:
        print(f"✅ Dual-GPU észlelve ({device_count} kártya). Vektorizáló az 1. GPU-ra (cuda:1) irányítva.")
        device = 'cuda:1' # Vektorizálás az egyiken, az LLM a másikon futhat majd
    else:
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

    print(f"🧠 Modell betöltése: {device}...")

    # Jelzések elkapása (Pause/Resume funkció)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    shutdown_event = mp.Event() # Megfelelően átadott mp.Event()

    processed_lines = get_processed_lines_state()
    print(f"🔍 Aktuális Checkpoint: {processed_lines} sor van már beolvasva a fájlból.")
    total_lines = get_total_lines(JSONL_FILE)

    if processed_lines >= total_lines:
        print("✅ Minden adat fel van dolgozva.")
        return

    # Multiprocessing Queue-k
    input_queue = mp.Queue(maxsize=PREFETCH_QUEUE_SIZE)
    import queue
    output_queue = queue.Queue(maxsize=WRITE_QUEUE_SIZE)

    reader = mp.Process(target=reader_process, args=(JSONL_FILE, input_queue, processed_lines, shutdown_event))
    reader.start()

    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension() if hasattr(model, 'get_sentence_embedding_dimension') else model.get_embedding_dimension()

    writer_thread = threading.Thread(target=writer_thread_worker, args=(output_queue, DB_FILE, INDEX_FILE, dim, shutdown_event))
    writer_thread.daemon = True
    writer_thread.start()

    start_time = time.time()
    print("🚀 GPU Encode Ciklus Indulése... (Nyomj Ctrl+C a biztonságos Pause-hoz!)")

    pbar = tqdm(total=total_lines - processed_lines, desc="Vektorizálás")

    try:
        while not shutdown_flag:
            item = input_queue.get()
            if item is None:
                break # EOF

            batch_texts, batch_metadata, processed_line = item

            # TISZTA GPU MÁTRIXSZORZÁS
            embeddings = model.encode(batch_texts, batch_size=BATCH_SIZE, show_progress_bar=False, normalize_embeddings=True)
            output_queue.put((batch_metadata, embeddings, processed_line))

            pbar.update(len(batch_texts))

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

    # Reader elakadásának feloldása
    try:
        while not input_queue.empty():
            input_queue.get_nowait()
    except:
        pass

    output_queue.put(None)
    writer_thread.join()
    reader.join()

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"⏱️ Futási idő: {elapsed/60:.2f} perc.")

if __name__ == "__main__":
    main()
