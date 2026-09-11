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

# Konfiguráció
TARGET_DIR = "/home/Jules/MX_LINUX_RAG"
DB_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_hybrid.db"
FAISS_BASE_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_vector"
REPO_LIST_PATH = "/home/Jules/MX_LINUX_RAG/vectorized_repos.txt"
EXTENSIONS = {'.py', '.c', '.h', '.cpp', '.sh', '.md', '.rst', '.json', '.yaml', '.txt', '.conf', '.mk', '.dts', '.dtsi'}

CHUNK_SIZE = 1500
BATCH_SIZE = 128
MAX_VECTORS_PER_SHARD = 1000000
RESTART_LIMIT = 10000

SHUTDOWN_REQUESTED = False

def signal_handler(sig, frame):
    global SHUTDOWN_REQUESTED
    if not SHUTDOWN_REQUESTED:
        print("\n\n[!] Megszakítás (Ctrl+C) észlelve! Biztonságos leállítás folyamatban...")
        SHUTDOWN_REQUESTED = True

signal.signal(signal.SIGINT, signal_handler)

def shutdown_machine():
    print("\n[!] Vektorizálás teljesen befejeződött. A gép leállítása (shutdown) indul...")
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

def init_db(db_path):
    conn = sqlite3.connect(db_path, timeout=120)
    conn.execute('PRAGMA journal_mode = WAL;')
    conn.execute('PRAGMA synchronous = OFF;')
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
    if not fully_processed_paths:
        return

    try:
        cursor.execute("BEGIN TRANSACTION;")
        cursor.executemany("INSERT OR IGNORE INTO rag_meta (path) VALUES (?)", [(p,) for p in fully_processed_paths])
        conn.commit()
    except Exception as e:
        print(f"Hiba a meta mentésnél: {e}")

    path = f"{FAISS_BASE_PATH}_{shard_id}.index"
    faiss.write_index(index, path)

    gc.collect()
    torch.cuda.empty_cache()

def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Hiba: A {TARGET_DIR} mappa nem létezik.")
        return

    conn, cursor = init_db(DB_PATH)
    processed_files = get_processed_files(cursor)

    # Két menet: először felmérjük az ÖSSZES hátralévőt a kijelzés miatt
    print("[*] Fájlok felmérése a kijelzéshez (ez pár másodpercet igénybe vehet)...")
    all_remaining_files = []
    repos = set()

    for f in get_files_generator(TARGET_DIR):
        if f not in processed_files:
            all_remaining_files.append(f)
            rel_path = os.path.relpath(f, TARGET_DIR)
            repos.add(rel_path.split(os.sep)[0])

    with open(REPO_LIST_PATH, 'a', encoding='utf-8') as f:
        for r in sorted(repos):
            f.write(r + '\n')

    if not all_remaining_files:
        print("[*] Minden fájl feldolgozva a teljes könyvtárban!")
        shutdown_machine()
        return

    total_remaining = len(all_remaining_files)
    print(f"\n=======================================================")
    print(f"[*] ÖSSZESEN FELDOLGOZANDÓ FÁJL: {total_remaining}")
    print(f"=======================================================\n")

    # Levágjuk a limitnél, hogy ne egye meg a RAM-ot
    if total_remaining > RESTART_LIMIT:
        remaining_files = all_remaining_files[:RESTART_LIMIT]
    else:
        remaining_files = all_remaining_files

    del all_remaining_files # Memória felszabadítás

    # PyTorch betöltése
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = True
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
    dimension = model.get_sentence_embedding_dimension()

    current_shard_id = get_current_shard_id()
    path = f"{FAISS_BASE_PATH}_{current_shard_id}.index"
    if os.path.exists(path):
        index = faiss.read_index(path)
    else:
        index = faiss.IndexFlatL2(dimension)

    # 10.000 Fájlos Stabil Verzió: Egyszerű, szinkron fájlolvasás, nincs háttérszál, nincs memóriaszivárgás
    current_batch_chunks = []
    current_batch_paths = []
    fully_processed_paths = set()

    # Itt a TOTAL a GLOBÁLIS mennyiséget mutatja (tehát nem 10.000, hanem pl. 400.000)
    pbar = tqdm(total=total_remaining, desc="Fájlok feldolgozása (Globális)")
    processed_files_in_batch = 0
    total_processed_this_run = 0

    for filepath in remaining_files:
        if SHUTDOWN_REQUESTED:
            break

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not content.strip():
                fully_processed_paths.add(filepath)
                processed_files_in_batch += 1
                total_processed_this_run += 1
                if processed_files_in_batch >= 50:
                    pbar.update(processed_files_in_batch)
                    processed_files_in_batch = 0
                continue

            chunks = chunk_text(content, CHUNK_SIZE)
            current_batch_chunks.extend(chunks)
            current_batch_paths.extend([filepath] * len(chunks))
            processed_files_in_batch += 1
            total_processed_this_run += 1

        except Exception:
            fully_processed_paths.add(filepath)
            processed_files_in_batch += 1
            total_processed_this_run += 1

        if processed_files_in_batch >= 50:
            pbar.update(processed_files_in_batch)
            processed_files_in_batch = 0

        # Ha összegyűlt 128 (vagy több) chunk, elküldjük a GPU-nak
        while len(current_batch_chunks) >= BATCH_SIZE:
            chunk_slice = current_batch_chunks[:BATCH_SIZE]
            path_slice = current_batch_paths[:BATCH_SIZE]

            vectors = model.encode(chunk_slice, batch_size=BATCH_SIZE, convert_to_numpy=True, show_progress_bar=False)
            faiss.normalize_L2(vectors)
            index.add(vectors)

            # Beszúrás az SQLite-ba (Autocommit)
            cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(path_slice, chunk_slice))

            for p in path_slice:
                fully_processed_paths.add(p)

            # Eltávolítjuk a már feldolgozott elemeket a listából
            del current_batch_chunks[:BATCH_SIZE]
            del current_batch_paths[:BATCH_SIZE]

            # 2000 fájlonként fizikai mentés
            if len(fully_processed_paths) >= 2000 or index.ntotal >= MAX_VECTORS_PER_SHARD:
                conn.commit()
                save_state(conn, index, current_shard_id, cursor, fully_processed_paths)
                fully_processed_paths.clear()

                # Shard váltás ha elérte az 1 milliót
                if index.ntotal >= MAX_VECTORS_PER_SHARD:
                    current_shard_id += 1
                    index = faiss.IndexFlatL2(dimension)

    # Maradék pbar frissítés
    if processed_files_in_batch > 0:
        pbar.update(processed_files_in_batch)
    pbar.close()

    # Maradék (128-nál kevesebb) chunk kódolása
    if current_batch_chunks and not SHUTDOWN_REQUESTED:
        vectors = model.encode(current_batch_chunks, batch_size=len(current_batch_chunks), convert_to_numpy=True, show_progress_bar=False)
        faiss.normalize_L2(vectors)
        index.add(vectors)
        cursor.executemany("INSERT INTO rag_docs (path, content) VALUES (?, ?)", zip(current_batch_paths, current_batch_chunks))
        for p in current_batch_paths:
            fully_processed_paths.add(p)

    conn.commit()
    save_state(conn, index, current_shard_id, cursor, fully_processed_paths)

    # Kilépési folyamat
    if SHUTDOWN_REQUESTED:
        sys.exit(0)
    elif total_processed_this_run >= RESTART_LIMIT:
        print(f"\n[*] Elértük a limitet ({RESTART_LIMIT} fájl). Szándékos kilépés (42) a Wrapper számára az újraindításhoz.")
        sys.exit(42)
    else:
        shutdown_machine()
        sys.exit(0)

if __name__ == "__main__":
    main()
