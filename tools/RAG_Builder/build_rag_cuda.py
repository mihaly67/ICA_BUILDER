import os
import sqlite3
import signal
import sys
import gc
import torch
import subprocess
import glob
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import queue
import threading

# Konfiguráció
TARGET_DIR = "/home/Jules/MX_LINUX_RAG"
DB_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_hybrid.db"
FAISS_BASE_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_vector"
REPO_LIST_PATH = "/home/Jules/MX_LINUX_RAG/vectorized_repos.txt"
EXTENSIONS = {'.py', '.c', '.h', '.cpp', '.sh', '.md', '.rst', '.json', '.yaml', '.txt', '.conf', '.mk', '.dts', '.dtsi'}

# === OPTIMALIZÁCIÓ INTEL XEON E5-1620 V3 HARDVERRE (AVX2, 32GB RAM Quad-Channel, PCIe 3.0) ===
CHUNK_SIZE = 1500
BATCH_SIZE = 128            # PCIe 3.0 és P2000 elbírja a nagyobb adatátvitelt!
MAX_VECTORS_PER_SHARD = 1000000 # 32GB RAM esetén az index fájlok nyugodtan nőhetnek 1 millió vektorig!

SHUTDOWN_REQUESTED = False

def signal_handler(sig, frame):
    global SHUTDOWN_REQUESTED
    if not SHUTDOWN_REQUESTED:
        print("\n\n[!] Megszakítás (Ctrl+C) észlelve! Biztonságos leállítás folyamatban...")
        SHUTDOWN_REQUESTED = True

signal.signal(signal.SIGINT, signal_handler)

def shutdown_machine():
    print("\n[!] Vektorizálás befejeződött. A gép leállítása (shutdown) indul...")
    try:
        cmd = "sudo shutdown -h now"
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"Hiba a leállítás során: {e}")

def drop_system_caches():
    try:
        subprocess.run("sync", shell=True, check=True)
        subprocess.run("sudo -n sh -c 'echo 1 > /proc/sys/vm/drop_caches'",
                       shell=True, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except Exception:
        pass

def get_files_generator(directory):
    for root, _, files in os.walk(directory):
        if '.git' in root or 'node_modules' in root or '__pycache__' in root:
            continue
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXTENSIONS:
                yield os.path.join(root, file)

def chunk_text(text, max_length):
    chunks = []
    for i in range(0, len(text), max_length):
        chunks.append(text[i:i+max_length])
    return chunks

# PRODUCER THREAD: Fájlok beolvasása, ami a Quad-Channel 32GB RAM és Xeon miatt villámgyors lesz
def file_reader_thread(remaining_files, data_queue):
    for filepath in remaining_files:
        if SHUTDOWN_REQUESTED:
            # Code Review: Ha leállás van, gyorsan ürítjük a szálat
            break
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if not content.strip():
                data_queue.put(('SKIP', filepath, []))
                continue

            chunks = chunk_text(content, CHUNK_SIZE)
            data_queue.put(('DATA', filepath, chunks))
        except Exception:
            data_queue.put(('SKIP', filepath, []))

    data_queue.put(('DONE', None, None))

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode = WAL;')
    conn.execute('PRAGMA synchronous = OFF;')
    # 32GB RAM esetén 500MB is lehet az SQLite cache a villámgyors I/O-ért!
    conn.execute('PRAGMA cache_size = -500000;')
    conn.execute('PRAGMA temp_store = MEMORY;')

    cursor = conn.cursor()
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS rag_docs USING fts5(
            path, content, tokenize='porter'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rag_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE
        )
    ''')
    conn.commit()
    return conn, cursor

def get_processed_files(cursor):
    cursor.execute("SELECT DISTINCT path FROM rag_meta")
    return {row[0] for row in cursor.fetchall()}

def get_current_shard_id():
    shards = glob.glob(f"{FAISS_BASE_PATH}_*.index")
    if not shards:
        return 1
    return max([int(s.split('_')[-1].split('.')[0]) for s in shards])

def save_state(conn, index, shard_id, cursor, fully_processed_paths):
    cursor.execute("BEGIN TRANSACTION;")
    cursor.executemany("INSERT OR IGNORE INTO rag_meta (path) VALUES (?)", [(p,) for p in fully_processed_paths])
    conn.commit()

    path = f"{FAISS_BASE_PATH}_{shard_id}.index"
    faiss.write_index(index, path)

    gc.collect()
    torch.cuda.empty_cache()
    drop_system_caches()

    print(f"\n[*] Állapot elmentve (Shard: {shard_id}).")

def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Hiba: A {TARGET_DIR} mappa nem létezik.")
        return

    print(f"[*] Fájlok keresése a {TARGET_DIR} könyvtárban...")

    conn, cursor = init_db(DB_PATH)
    processed_files = get_processed_files(cursor)

    all_files_count = 0
    remaining_files = []
    repos = set()

    for f in get_files_generator(TARGET_DIR):
        all_files_count += 1
        if f not in processed_files:
            remaining_files.append(f)
            rel_path = os.path.relpath(f, TARGET_DIR)
            repos.add(rel_path.split(os.sep)[0])

    with open(REPO_LIST_PATH, 'w', encoding='utf-8') as f:
        for r in sorted(repos):
            f.write(r + '\n')

    print(f"[*] Összes fájl: {all_files_count} | Már feldolgozva: {len(processed_files)} | Hátralévő: {len(remaining_files)}")
    if not remaining_files:
        print("[*] Minden fájl feldolgozva!")
        shutdown_machine()
        return

    print("[*] SentenceTransformer modell betöltése GPU-n (CUDA)...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
    dimension = model.get_sentence_embedding_dimension()

    # === VISSZATÉRÉS AZ INDEXFLATL2-RE AVX2 MELLETT ===
    # A Xeon E5-1620 V3 processzor támogatja az AVX2 utasításkészletet.
    # Így a FlatL2 (veszteségmentes) indexelés villámgyors lesz a CPU-n!
    # Nincs szükség többé az IVFPQ kvantálásra és hosszas betanításra (train).

    current_shard_id = get_current_shard_id()
    path = f"{FAISS_BASE_PATH}_{current_shard_id}.index"
    if os.path.exists(path):
        print(f"[*] Meglévő FAISS shard ({current_shard_id}) betöltése a lemezről...")
        index = faiss.read_index(path)
    else:
        print(f"[*] Új FAISS IndexFlatL2 shard ({current_shard_id}) létrehozása (AVX2 optimalizált)...")
        index = faiss.IndexFlatL2(dimension)

    # Indítjuk a Producer szálat (I/O olvasás és chunkolás a háttérben)
    # A 32GB RAM miatt hatalmas sort csinálhatunk az I/O várakozás nullázásához
    data_queue = queue.Queue(maxsize=50000)
    # Code Review javítás: daemon szál, hogy kilépéskor ne lógjon a levegőben a script
    producer = threading.Thread(target=file_reader_thread, args=(remaining_files, data_queue), daemon=True)
    producer.start()

    current_batch_chunks = []
    current_batch_paths = []
    fully_processed_paths = set()

    cursor.execute("BEGIN TRANSACTION;")

    pbar = tqdm(total=len(remaining_files), desc="Fájlok feldolgozása")

    while True:
        if SHUTDOWN_REQUESTED:
            # Code Review javítás: Megszakítás esetén ürítjük a sort,
            # és csak azokat a fájlokat mentjük, amik már GARANTÁLTAN bekerültek a batchbe és az FTS-be!
            break

        try:
            status, filepath, chunks = data_queue.get(timeout=5)
        except queue.Empty:
            if not producer.is_alive():
                break
            continue

        if status == 'DONE':
            break

        if status == 'SKIP':
            fully_processed_paths.add(filepath)
            pbar.update(1)
            continue

        # Adatok betöltése a batch-be
        for chunk in chunks:
            current_batch_chunks.append(chunk)
            current_batch_paths.append(filepath)

            # Ha megtelt a batch, azonnal CUDA GPU execute
            if len(current_batch_chunks) >= BATCH_SIZE:
                vectors = model.encode(current_batch_chunks, batch_size=BATCH_SIZE, convert_to_numpy=True, show_progress_bar=False)
                faiss.normalize_L2(vectors)
                index.add(vectors)

                cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(current_batch_paths, current_batch_chunks))

                # Mentjük a fájlok útvonalát amik bekerültek
                for p in set(current_batch_paths):
                    fully_processed_paths.add(p)

                current_batch_chunks.clear()
                current_batch_paths.clear()

        pbar.update(1)

        # Mentés és shard váltás
        # A 32GB RAM miatt ritkíthatjuk a diszkre írást, 5000 fájlonként commitolunk!
        if len(fully_processed_paths) >= 5000 or index.ntotal >= MAX_VECTORS_PER_SHARD:
            conn.commit()
            save_state(conn, index, current_shard_id, cursor, fully_processed_paths)
            fully_processed_paths.clear()

            if index.ntotal >= MAX_VECTORS_PER_SHARD:
                current_shard_id += 1
                index = faiss.IndexFlatL2(dimension)

            cursor.execute("BEGIN TRANSACTION;")

    # Maradék feldolgozása, ha nem volt megszakítás
    if current_batch_chunks and not SHUTDOWN_REQUESTED:
        vectors = model.encode(current_batch_chunks, batch_size=BATCH_SIZE, convert_to_numpy=True, show_progress_bar=False)
        faiss.normalize_L2(vectors)
        index.add(vectors)
        cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(current_batch_paths, current_batch_chunks))
        for p in set(current_batch_paths):
            fully_processed_paths.add(p)

    conn.commit()
    save_state(conn, index, current_shard_id, cursor, fully_processed_paths)

    if not SHUTDOWN_REQUESTED:
        shutdown_machine()
    else:
        # Tisztítás daemon szál mellett (a Python sys.exit is elég lenne)
        sys.exit(0)

if __name__ == "__main__":
    main()
