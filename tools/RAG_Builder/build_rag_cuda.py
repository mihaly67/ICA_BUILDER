import os
import sqlite3
import signal
import sys
import gc
import torch
import subprocess
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

TARGET_DIR = "/home/Jules/MX_LINUX_RAG"
DB_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_hybrid.db"
FAISS_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_vector.index"
REPO_LIST_PATH = "/home/Jules/MX_LINUX_RAG/vectorized_repos.txt"
EXTENSIONS = {'.py', '.c', '.h', '.cpp', '.sh', '.md', '.rst', '.json', '.yaml', '.txt', '.conf', '.mk', '.dts', '.dtsi'}

CHUNK_SIZE = 1500
BATCH_SIZE = 32

# Felemeljük a pufferelést: kevesebbszer mentjük le a FAISS/SQLite adatokat, hogy
# ne I/O thrashing legyen a 2+ GB-os fájlok írása/olvasása miatt.
MAX_CHUNKS_IN_RAM = 2000

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

def get_files_and_repos(directory):
    file_list = []
    vectorized_repos = set()
    for root, _, files in os.walk(directory):
        if '.git' in root or 'node_modules' in root or '__pycache__' in root:
            continue
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXTENSIONS:
                full_path = os.path.join(root, file)
                file_list.append(full_path)

                rel_path = os.path.relpath(root, directory)
                repo_name = rel_path.split(os.sep)[0]
                vectorized_repos.add(repo_name)

    return file_list, vectorized_repos

def chunk_text(text, max_length):
    chunks = []
    for i in range(0, len(text), max_length):
        chunks.append(text[i:i+max_length])
    return chunks

def init_db(db_path):
    conn = sqlite3.connect(db_path)

    # ---------------------------------------------------------
    # EXTRÉM SQLITE OPTIMALIZÁCIÓ (Sebesség növelése ~100x-osra)
    # ---------------------------------------------------------
    conn.execute('PRAGMA journal_mode = WAL;') # Write-Ahead Logging: drasztikusan gyorsabb I/O
    conn.execute('PRAGMA synchronous = OFF;')  # Nem várja meg az OS írási visszaigazolását (csak app crasnál veszélyes picit, de van backupunk az indexben)
    conn.execute('PRAGMA cache_size = 100000;') # Hatalmas RAM cache az SQLite-nak (kb 100MB)
    conn.execute('PRAGMA temp_store = MEMORY;') # A temp műveleteket RAM-ban végzi Swap helyett

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

def save_state(conn, index, faiss_path, cursor, fully_processed_paths):
    for p in fully_processed_paths:
        cursor.execute("INSERT OR IGNORE INTO rag_meta (path) VALUES (?)", (p,))

    conn.commit()
    faiss.write_index(index, faiss_path)

    gc.collect()
    torch.cuda.empty_cache()
    drop_system_caches()

    print("\n[*] Állapot biztonságosan elmentve (Következő fázis).")

def process_batch(model, index, cursor, batch_chunks, batch_paths):
    vectors = model.encode(batch_chunks, convert_to_numpy=True)
    faiss.normalize_L2(vectors)
    index.add(vectors)

    # SQLite tömeges írás optimalizálása (executemany sokkal gyorsabb mint for loop execute)
    cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(batch_paths, batch_chunks))

def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Hiba: A {TARGET_DIR} mappa nem létezik.")
        return

    print(f"[*] Fájlok keresése a {TARGET_DIR} könyvtárban...")
    files, repos = get_files_and_repos(TARGET_DIR)

    with open(REPO_LIST_PATH, 'w', encoding='utf-8') as f:
        for r in sorted(repos):
            f.write(r + '\n')

    print("[*] SQLite adatbázis inicializálása extrém I/O sebességgel (WAL, Sync=OFF)...")
    conn, cursor = init_db(DB_PATH)

    processed_files = get_processed_files(cursor)
    remaining_files = [f for f in files if f not in processed_files]

    print(f"[*] Összes fájl: {len(files)} | Már feldolgozva: {len(processed_files)} | Hátralévő: {len(remaining_files)}")
    if len(remaining_files) == 0:
        print("[*] Minden fájl feldolgozva!")
        shutdown_machine()
        return

    print("[*] SentenceTransformer modell betöltése GPU-n (CUDA)...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
    dimension = model.get_sentence_embedding_dimension()

    if os.path.exists(FAISS_PATH):
        print("[*] Meglévő FAISS index betöltése a lemezről (Ez eltarthat egy percig is)...")
        index = faiss.read_index(FAISS_PATH)
    else:
        print("[*] Új FAISS index létrehozása...")
        index = faiss.IndexFlatL2(dimension)

    print("[*] Szövegek előkészítése és vektorizálása...")

    current_batch_chunks = []
    current_batch_paths = []

    fully_processed_paths = set()
    files_processed_since_save = 0

    # Csak 2000 FÁJLONKÉNT mentünk (eddig 300 volt). A FAISS write és SQLite Commit
    # több gigabájtos fájloknál súlyos másodperceket vesz igénybe.
    SAVE_INTERVAL_FILES = 2000

    for filepath in tqdm(remaining_files, desc="Fájlok feldolgozása", miniters=10):
        if SHUTDOWN_REQUESTED:
            current_batch_chunks = []
            current_batch_paths = []
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

            batch_texts = current_batch_chunks[:BATCH_SIZE]
            batch_paths = current_batch_paths[:BATCH_SIZE]

            # Ez is sokat gyorsít, mert batch-elve küldjük be az SQLite-ba a process_batch alatt
            process_batch(model, index, cursor, batch_texts, batch_paths)

            current_batch_chunks = current_batch_chunks[BATCH_SIZE:]
            current_batch_paths = current_batch_paths[BATCH_SIZE:]

        if SHUTDOWN_REQUESTED:
            current_batch_chunks = []
            current_batch_paths = []
            break

        fully_processed_paths.add(filepath)
        files_processed_since_save += 1

        if files_processed_since_save >= SAVE_INTERVAL_FILES or len(current_batch_chunks) >= MAX_CHUNKS_IN_RAM:
            while len(current_batch_chunks) > 0:
                chunk_sz = min(BATCH_SIZE, len(current_batch_chunks))
                batch_texts = current_batch_chunks[:chunk_sz]
                batch_paths = current_batch_paths[:chunk_sz]

                process_batch(model, index, cursor, batch_texts, batch_paths)

                current_batch_chunks = current_batch_chunks[chunk_sz:]
                current_batch_paths = current_batch_paths[chunk_sz:]

            save_state(conn, index, FAISS_PATH, cursor, fully_processed_paths)
            fully_processed_paths.clear()
            files_processed_since_save = 0

    if len(current_batch_chunks) > 0 and not SHUTDOWN_REQUESTED:
        while len(current_batch_chunks) > 0:
            chunk_sz = min(BATCH_SIZE, len(current_batch_chunks))
            batch_texts = current_batch_chunks[:chunk_sz]
            batch_paths = current_batch_paths[:chunk_sz]

            process_batch(model, index, cursor, batch_texts, batch_paths)

            current_batch_chunks = current_batch_chunks[chunk_sz:]
            current_batch_paths = current_batch_paths[chunk_sz:]

    save_state(conn, index, FAISS_PATH, cursor, fully_processed_paths)

    if not SHUTDOWN_REQUESTED:
        shutdown_machine()

if __name__ == "__main__":
    main()
