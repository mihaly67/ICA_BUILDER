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

TARGET_DIR = "/home/Jules/MX_LINUX_RAG"
DB_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_hybrid.db"
FAISS_BASE_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_vector"
REPO_LIST_PATH = "/home/Jules/MX_LINUX_RAG/vectorized_repos.txt"
EXTENSIONS = {'.py', '.c', '.h', '.cpp', '.sh', '.md', '.rst', '.json', '.yaml', '.txt', '.conf', '.mk', '.dts', '.dtsi'}

CHUNK_SIZE = 1500
BATCH_SIZE = 96
MAX_VECTORS_PER_SHARD = 500000

SHUTDOWN_REQUESTED = False

def signal_handler(sig, frame):
    global SHUTDOWN_REQUESTED
    if not SHUTDOWN_REQUESTED:
        print("\n\n[!] Megszakítás (Ctrl+C) észlelve! Biztonságos leállítás...")
        SHUTDOWN_REQUESTED = True

signal.signal(signal.SIGINT, signal_handler)

def shutdown_machine():
    print("\n[!] Vektorizálás befejeződött. A gép leállítása (shutdown) indul...")
    try:
        cmd = "sudo shutdown -h now"
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"Hiba a leállítás során: {e}")

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

# PRODUCER THREAD: Fájlok beolvasása és darabolása memóriába aszinkron módon
def file_reader_thread(remaining_files, data_queue):
    for filepath in remaining_files:
        if SHUTDOWN_REQUESTED:
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
    conn.execute('PRAGMA cache_size = 50000;')

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

def create_ivfpq_index(dimension, model, sample_texts):
    quantizer = faiss.IndexFlatL2(dimension)
    index = faiss.IndexIVFPQ(quantizer, dimension, 100, 8, 8)

    print(f"[*] FAISS IVFPQ index betanítása {len(sample_texts)} mintával...")
    sample_vectors = model.encode(sample_texts, batch_size=BATCH_SIZE, convert_to_numpy=True)
    faiss.normalize_L2(sample_vectors)
    index.train(sample_vectors)
    return index

def save_state(conn, index, shard_id, cursor, fully_processed_paths):
    cursor.execute("BEGIN TRANSACTION;")
    cursor.executemany("INSERT OR IGNORE INTO rag_meta (path) VALUES (?)", [(p,) for p in fully_processed_paths])
    conn.commit()

    faiss.write_index(index, f"{FAISS_BASE_PATH}_{shard_id}.index")
    gc.collect()
    torch.cuda.empty_cache()

def main():
    if not os.path.exists(TARGET_DIR):
        return

    print(f"[*] Fájlok keresése a {TARGET_DIR} könyvtárban...")
    all_files_count = 0
    remaining_files = []

    conn, cursor = init_db(DB_PATH)
    processed_files = get_processed_files(cursor)

    for f in get_files_generator(TARGET_DIR):
        all_files_count += 1
        if f not in processed_files:
            remaining_files.append(f)

    print(f"[*] Összes fájl: {all_files_count} | Már feldolgozva: {len(processed_files)} | Hátralévő: {len(remaining_files)}")
    if not remaining_files:
        shutdown_machine()
        return

    print("[*] SentenceTransformer modell betöltése GPU-n (CUDA)...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
    dimension = model.get_sentence_embedding_dimension()

    # Train data gathering
    sample_texts = []
    for filepath in remaining_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                c = f.read()
                if c.strip():
                    sample_texts.extend(chunk_text(c, CHUNK_SIZE))
            if len(sample_texts) > 4500:
                sample_texts = sample_texts[:4500]
                break
        except:
            pass
    if len(sample_texts) < 4500:
        sample_texts.extend(["padding"] * (4500 - len(sample_texts)))

    current_shard_id = get_current_shard_id()
    path = f"{FAISS_BASE_PATH}_{current_shard_id}.index"
    if os.path.exists(path):
        index = faiss.read_index(path)
    else:
        index = create_ivfpq_index(dimension, model, sample_texts)

    # Indítjuk a Producer szálat (I/O olvasás és chunkolás a háttérben)
    data_queue = queue.Queue(maxsize=10000)
    producer = threading.Thread(target=file_reader_thread, args=(remaining_files, data_queue))
    producer.start()

    current_batch_chunks = []
    current_batch_paths = []
    fully_processed_paths = set()

    cursor.execute("BEGIN TRANSACTION;")

    pbar = tqdm(total=len(remaining_files), desc="Fájlok feldolgozása")

    while True:
        if SHUTDOWN_REQUESTED:
            break

        try:
            status, filepath, chunks = data_queue.get(timeout=5)
        except queue.Empty:
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

            # Ha megtelt a batch, azonnal CUDA GPU execute (A GPU nem vár a lassú fájlolvasásra!)
            if len(current_batch_chunks) >= BATCH_SIZE:
                # model.encode batch_size paramétere PyTorch DataLoader szinten optimalizál
                vectors = model.encode(current_batch_chunks, batch_size=BATCH_SIZE, convert_to_numpy=True, show_progress_bar=False)
                faiss.normalize_L2(vectors)
                index.add(vectors)

                cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(current_batch_paths, current_batch_chunks))

                current_batch_chunks.clear()
                current_batch_paths.clear()

        fully_processed_paths.add(filepath)
        pbar.update(1)

        # Mentés és shard váltás
        if len(fully_processed_paths) >= 2000 or index.ntotal >= MAX_VECTORS_PER_SHARD:
            conn.commit()
            save_state(conn, index, current_shard_id, cursor, fully_processed_paths)
            fully_processed_paths.clear()

            if index.ntotal >= MAX_VECTORS_PER_SHARD:
                current_shard_id += 1
                index = create_ivfpq_index(dimension, model, sample_texts)

            cursor.execute("BEGIN TRANSACTION;")

    # Maradék feldolgozása, ha nem volt megszakítás
    if current_batch_chunks and not SHUTDOWN_REQUESTED:
        vectors = model.encode(current_batch_chunks, batch_size=BATCH_SIZE, convert_to_numpy=True, show_progress_bar=False)
        faiss.normalize_L2(vectors)
        index.add(vectors)
        cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(current_batch_paths, current_batch_chunks))

    conn.commit()
    save_state(conn, index, current_shard_id, cursor, fully_processed_paths)

    if not SHUTDOWN_REQUESTED:
        shutdown_machine()

if __name__ == "__main__":
    main()
