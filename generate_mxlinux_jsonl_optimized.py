import os
import json
import uuid
import sys

# Célkönyvtár, ahol az MX Linux repók vannak
BASE_DIR = "/home/Jules/MX_LINUX_RAG"
OUTPUT_FILE = os.path.join(BASE_DIR, "mxlinux_dev.jsonl")

# Kiterjesztések szigorú szűrése (kizárjuk a nagy binárisokat vagy log fájlokat, amik bejuthattak)
ALLOWED_EXTENSIONS = {
    ".py", ".sh", ".c", ".cpp", ".h", ".hpp", ".js", ".ts",
    ".html", ".css", ".md", ".txt", ".json", ".yaml", ".yml",
    ".xml", ".ini", ".conf", ".desktop"
}

def generate_jsonl():
    print(f"Bemeneti könyvtár keresése: {BASE_DIR}")
    print(f"Kimeneti fájl: {OUTPUT_FILE}")

    total_files = 0
    total_chunks = 0

    # 5MB-os limit fájlonként a hibrid szemétdomb ellen
    MAX_FILE_SIZE = 5 * 1024 * 1024

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(BASE_DIR):
            # Kizárjuk a nem releváns vagy nagy mappákat
            if any(x in root for x in ['.git', 'venv', 'jules_venv', 'node_modules', '__pycache__', 'build', 'dist']):
                continue

            # Pontos repo név és relatív struktúra meghatározása
            rel_dir = os.path.relpath(root, BASE_DIR)
            if rel_dir == '.':
                repo_name = "root"
                repo_internal_path = ""
            else:
                parts = rel_dir.split(os.sep)
                repo_name = parts[0]
                repo_internal_path = os.sep.join(parts[1:]) if len(parts) > 1 else ""

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue

                file_path = os.path.join(root, file)

                # Méret ellenőrzés a hatalmas JSON/TXT logok elkerülésére
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > MAX_FILE_SIZE:
                        print(f"Figyelem: {file_path} túl nagy ({file_size} bytes), kihagyva.")
                        continue
                except OSError:
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                        if not content.strip():
                            continue

                        total_files += 1

                        MAX_CHARS = 2000 # Kisebb chunkok a hatékonyabb vektorizáláshoz
                        for i in range(0, len(content), MAX_CHARS):
                            chunk = content[i:i+MAX_CHARS]
                            chunk_id = str(uuid.uuid4())

                            # A fájlútvonal a repo-n belüli pontos helye
                            internal_file_path = os.path.join(repo_internal_path, file)

                            metadata = {
                                "repo": repo_name,
                                "file_path": internal_file_path,
                                "extension": ext
                            }

                            row = {
                                "id": chunk_id,
                                "text": chunk,
                                "metadata": metadata
                            }

                            outfile.write(json.dumps(row, ensure_ascii=False) + "\n")
                            total_chunks += 1

                except Exception as e:
                    pass

    print(f"Kész! Feldolgozott fájlok: {total_files}, Létrehozott Chunkok: {total_chunks}")

if __name__ == "__main__":
    generate_jsonl()
