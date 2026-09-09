import os
import sqlite3
import signal
import sys
import gc
import torch
import subprocess
import glob
from collections import deque
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

TARGET_DIR = "/home/Jules/MX_LINUX_RAG"
DB_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_hybrid.db"
FAISS_BASE_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_vector"
REPO_LIST_PATH = "/home/Jules/MX_LINUX_RAG/vectorized_repos.txt"
EXTENSIONS = {'.py', '.c', '.h', '.cpp', '.sh', '.md', '.rst', '.json', '.yaml', '.txt', '.conf', '.mk', '.dts', '.dtsi'}

CHUNK_SIZE = 1500
BATCH_SIZE = 96
MAX_CHUNKS_IN_RAM = 500
MAX_VECTORS_PER_SHARD = 500000

SHUTDOWN_REQUESTED = False

def signal_handler(sig, frame):
    global SHUTDOWN_REQUESTED
    if not SHUTDOWN_REQUESTED:
        print("\n\n[!] Megszakítás (Ctrl+C) észlelve! Kérlek, várj amíg a program biztonságosan elmenti az eddigi adatokat...")
        SHUTDOWN_REQUESTED = True
    else:
        print("\n[!] Már folyamatban van a mentés és leállítás. Türelem...")

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

# JAVÍTÁS 1: A get_files generátorrá alakítása!
# Mivel 713,000 fájl memóriában tartása (és az os.walk futtatása egyszerre) feleslegesen lassít és szemetel.
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

def init_db(db_path):
    conn = sqlite3.connect(db_path)

    # JAVÍTÁS 2: FTS5 lassulás ellen EXTRÉM SQLite PRAGMÁK
    conn.execute('PRAGMA journal_mode = WAL;')
    conn.execute('PRAGMA synchronous = OFF;') # Kikapcsoljuk az Fsync-et, az I/O blokkolást teljesen megszünteti
    conn.execute('PRAGMA cache_size = -200000;') # 200MB RAM dedikálása az SQLite-nak a thrashing ellen
    conn.execute('PRAGMA temp_store = MEMORY;')
    conn.execute('PRAGMA mmap_size = 30000000000;') # MMAP bekapcsolása gigantikus DB-hez (30GB-ig)

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
    rows = cursor.fetchall()
    return set([row[0] for row in rows])

def get_current_shard_id():
    shards = glob.glob(f"{FAISS_BASE_PATH}_*.index")
    if not shards:
        return 1

    max_id = 1
    for s in shards:
        try:
            num = int(s.split('_')[-1].split('.')[0])
            if num > max_id:
                max_id = num
        except:
            pass
    return max_id

def create_ivfpq_index(dimension, model, sample_texts):
    nlist = 100
    m = 8

    quantizer = faiss.IndexFlatL2(dimension)
    index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, 8)

    print(f"[*] FAISS IVFPQ (Kvantált) index betanítása {len(sample_texts)} mintával...")

    sample_vectors = []
    for i in range(0, len(sample_texts), BATCH_SIZE):
        batch = sample_texts[i:i+BATCH_SIZE]
        vecs = model.encode(batch, convert_to_numpy=True)
        faiss.normalize_L2(vecs)
        sample_vectors.append(vecs)

    final_sample_vectors = np.vstack(sample_vectors)

    index.train(final_sample_vectors)
    return index

def load_or_create_index(shard_id, dimension, model, sample_texts=None):
    path = f"{FAISS_BASE_PATH}_{shard_id}.index"
    if os.path.exists(path):
        print(f"[*] Meglévő FAISS shard ({shard_id}) betöltése a lemezről...")
        return faiss.read_index(path)
    else:
        print(f"[*] Új FAISS IVFPQ shard ({shard_id}) létrehozása...")
        if sample_texts is None:
            sample_texts = ["sample text padding"] * 4500
        return create_ivfpq_index(dimension, model, sample_texts)

def save_state(conn, index, shard_id, cursor, fully_processed_paths):
    # Tranzakció a DB-nek, hogy a sebesség iszonyatos maradjon
    cursor.execute("BEGIN TRANSACTION;")
    for p in fully_processed_paths:
        cursor.execute("INSERT OR IGNORE INTO rag_meta (path) VALUES (?)", (p,))
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

    print("[*] SQLite adatbázis inicializálása EXTRÉM I/O sebességgel (WAL, MMAP, Sync=OFF)...")
    conn, cursor = init_db(DB_PATH)

    processed_files = get_processed_files(cursor)

    # Listázzuk a fájlokat gyorsan az elején csak a számlálóhoz
    print(f"[*] Fájlfa bejárása...")
    all_files_count = 0
    remaining_files = []

    for f in get_files_generator(TARGET_DIR):
        all_files_count += 1
        if f not in processed_files:
            remaining_files.append(f)

    # Gyűjtsünk össze repókat a log txt-hez
    repos = set()
    for f in remaining_files[:5000]: # Elég az első párból kitalálni a repókat
        rel_path = os.path.relpath(f, TARGET_DIR)
        repos.add(rel_path.split(os.sep)[0])

    with open(REPO_LIST_PATH, 'w', encoding='utf-8') as f:
        for r in sorted(repos):
            f.write(r + '\n')

    print(f"[*] Összes fájl: {all_files_count} | Már feldolgozva: {len(processed_files)} | Hátralévő: {len(remaining_files)}")
    if len(remaining_files) == 0:
        print("[*] Minden fájl feldolgozva!")
        shutdown_machine()
        return

    print("[*] SentenceTransformer modell betöltése GPU-n (CUDA)...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
    dimension = model.get_sentence_embedding_dimension()

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
        sample_texts.extend(["padding data for fast text embedding generation in python"] * (4500 - len(sample_texts)))

    current_shard_id = get_current_shard_id()
    index = load_or_create_index(current_shard_id, dimension, model, sample_texts)

    print("[*] Szövegek előkészítése és vektorizálása (Sharding és Kvantálás aktív)...")

    current_batch_chunks = deque()
    current_batch_paths = deque()

    fully_processed_paths = set()
    files_processed_since_save = 0
    SAVE_INTERVAL_FILES = 2000

    # Explicit SQLite tranzakció indul! Ezzel oldjuk meg a lelassulást.
    cursor.execute("BEGIN TRANSACTION;")

    for filepath in tqdm(remaining_files, desc="Fájlok feldolgozása", miniters=10):
        if SHUTDOWN_REQUESTED:
            current_batch_chunks.clear()
            current_batch_paths.clear()
            break

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            fully_processed_paths.add(filepath)
            continue

        if not content.strip():
            fully_processed_paths.add(filepath)
            continue

        chunks = chunk_text(content, CHUNK_SIZE)
        current_batch_chunks.extend(chunks)
        current_batch_paths.extend([filepath] * len(chunks))

        while len(current_batch_chunks) >= BATCH_SIZE:
            if SHUTDOWN_REQUESTED:
                break

            batch_texts = [current_batch_chunks.popleft() for _ in range(BATCH_SIZE)]
            batch_paths = [current_batch_paths.popleft() for _ in range(BATCH_SIZE)]

            vectors = model.encode(batch_texts, convert_to_numpy=True)
            faiss.normalize_L2(vectors)
            index.add(vectors)

            cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(batch_paths, batch_texts))

        if SHUTDOWN_REQUESTED:
            current_batch_chunks.clear()
            current_batch_paths.clear()
            break

        fully_processed_paths.add(filepath)
        files_processed_since_save += 1

        # Periodikus mini-commit az adatbázis megfagyása ellen (itt zárjuk le a tranzakciót és indítunk újat)
        if len(fully_processed_paths) % 100 == 0:
            conn.commit()
            cursor.execute("BEGIN TRANSACTION;")

        if index.ntotal >= MAX_VECTORS_PER_SHARD:
            while len(current_batch_chunks) > 0:
                chunk_sz = min(BATCH_SIZE, len(current_batch_chunks))
                batch_texts = [current_batch_chunks.popleft() for _ in range(chunk_sz)]
                batch_paths = [current_batch_paths.popleft() for _ in range(chunk_sz)]

                vectors = model.encode(batch_texts, convert_to_numpy=True)
                faiss.normalize_L2(vectors)
                index.add(vectors)
                cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(batch_paths, batch_texts))

            conn.commit() # Lezárjuk a futó tranzakciót a save előtt
            save_state(conn, index, current_shard_id, cursor, fully_processed_paths)
            fully_processed_paths.clear()
            files_processed_since_save = 0

            current_shard_id += 1
            index = create_ivfpq_index(dimension, model, sample_texts)
            cursor.execute("BEGIN TRANSACTION;") # Új tranzakció a következő shardhoz

        elif files_processed_since_save >= SAVE_INTERVAL_FILES or len(current_batch_chunks) >= MAX_CHUNKS_IN_RAM:
            while len(current_batch_chunks) > 0:
                chunk_sz = min(BATCH_SIZE, len(current_batch_chunks))
                batch_texts = [current_batch_chunks.popleft() for _ in range(chunk_sz)]
                batch_paths = [current_batch_paths.popleft() for _ in range(chunk_sz)]

                vectors = model.encode(batch_texts, convert_to_numpy=True)
                faiss.normalize_L2(vectors)
                index.add(vectors)
                cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(batch_paths, batch_texts))

            conn.commit() # Tranzakció lezárás a save előtt
            save_state(conn, index, current_shard_id, cursor, fully_processed_paths)
            fully_processed_paths.clear()
            files_processed_since_save = 0
            cursor.execute("BEGIN TRANSACTION;")

    if len(current_batch_chunks) > 0 and not SHUTDOWN_REQUESTED:
        while len(current_batch_chunks) > 0:
            chunk_sz = min(BATCH_SIZE, len(current_batch_chunks))
            batch_texts = [current_batch_chunks.popleft() for _ in range(chunk_sz)]
            batch_paths = [current_batch_paths.popleft() for _ in range(chunk_sz)]

            vectors = model.encode(batch_texts, convert_to_numpy=True)
            faiss.normalize_L2(vectors)
            index.add(vectors)
            cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(batch_paths, batch_texts))

    conn.commit()
    save_state(conn, index, current_shard_id, cursor, fully_processed_paths)

    if not SHUTDOWN_REQUESTED:
        shutdown_machine()

if __name__ == "__main__":
    main()
