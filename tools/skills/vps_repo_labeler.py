#!/usr/bin/env python3
import os
import json
import sys
import urllib.request
import urllib.error
import re

# Ez a script KIZÁRÓLAG a VPS-en fut.

# Dinamikusan vesszük át a környezeti változóból vagy argumentumból, de alapból a MAIN RAG-ra mutat
TARGET_DIR = os.environ.get("TARGET_DIR", "/home/misi/Rag_epites, chatbot_csv_data_llm_RAG/")
OUTPUT_JSON = os.path.join(TARGET_DIR, "REPO_LABELS.json")
MODEL = "llama3:latest"

def query_local_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    # A format: json beállítással próbáljuk kényszeríteni a modelt a helyes szintaktikára
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode('utf-8'))
        return result.get("response", "").strip()
    except Exception as e:
        return f"Error: {str(e)}"

def extract_json(response_text):
    """Próbálja kinyerni a JSON objektumot a szövegből regex segítségével, ha a modell túlbeszélne."""
    try:
        # Ha tiszta JSON jön
        return json.loads(response_text)
    except:
        try:
            # Keressük az első { és az utolsó } közötti részt
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except:
            pass
    return None

def process_repos(limit_to_dirs=None):
    labels = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
                labels = json.load(f)
        except:
            pass

    print(f"🔍 Repók beolvasása innen: {TARGET_DIR}")

    dirs_to_process = []
    if limit_to_dirs:
        dirs_to_process = limit_to_dirs
    else:
        dirs_to_process = [d for d in os.listdir(TARGET_DIR) if os.path.isdir(os.path.join(TARGET_DIR, d))]

    for repo_name in dirs_to_process:
        if repo_name.startswith('.'): continue
        if repo_name in labels and "Failed" not in labels[repo_name].get("summary", ""):
            print(f"⏭️ {repo_name} már sikeresen fel van címkézve. Kihagyás.")
            continue

        repo_path = os.path.join(TARGET_DIR, repo_name)
        readme_path = None

        for name in ["README.md", "readme.md", "README.MD"]:
            p = os.path.join(repo_path, name)
            if os.path.exists(p):
                readme_path = p
                break

        if not readme_path:
            print(f"⚠️ Nincs README a(z) {repo_name} repóban.")
            labels[repo_name] = {"summary": "No README found", "tags": []}
            continue

        print(f"🧠 {repo_name} feldolgozása a(z) {MODEL} modellel...")
        try:
            with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 2000 karakter elég egy jó summary-hez
                content = f.read()[:2000]

            prompt = f"""You are an expert GitHub librarian.
Analyze the following README excerpt. Output a valid JSON object with exactly these two keys:
"summary": A concise one-sentence description of the repository.
"tags": An array of exactly 3 relevant technical keywords.

README EXCERPT:
{content}
"""
            response = query_local_ollama(prompt)
            parsed = extract_json(response)

            if parsed and "summary" in parsed and "tags" in parsed:
                labels[repo_name] = parsed
                print(f"✅ SIKER: {repo_name} -> {parsed.get('tags', [])}")
            else:
                print(f"❌ JSON parse hiba a modell válaszánál ({repo_name}). Nyers válasz részlete: {response[:100]}...")
                labels[repo_name] = {"summary": "Failed to parse LLM response", "tags": [], "raw": response[:150]}

            # Részleges mentés minden sikeres/sikertelen iteráció után, ha menet közben leállna
            with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
                json.dump(labels, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"Hiba a fájl olvasásakor: {e}")

    print(f"🎉 Feldolgozás befejezve. Címkék elmentve: {OUTPUT_JSON}")
    print(f"💡 Futtatási tipp hosszú műveletekhez: 'nohup python3 vps_repo_labeler.py > labeler.log 2>&1 &'")

if __name__ == "__main__":
    target_repos = sys.argv[1:] if len(sys.argv) > 1 else None
    process_repos(limit_to_dirs=target_repos)
