#!/usr/bin/env python3
import os
import json
import sys
import urllib.request
import urllib.error

# Ez a script KIZÁRÓLAG a VPS-en fut. Nem SSH-n keresztül hívja az Ollamát, hanem lokálisan!

TARGET_DIR = "/home/misi/Rag_epites, chatbot_csv_data_llm_RAG/"
OUTPUT_JSON = os.path.join(TARGET_DIR, "REPO_LABELS.json")
MODEL = "llama3:latest" # Inkább a Llama3-at használjuk, a qwen2.5 hallucintál magyarul

def query_local_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode('utf-8'))
        return result.get("response", "").strip()
    except Exception as e:
        return f"Error: {str(e)}"

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
        if repo_name in labels:
            print(f"⏭️ {repo_name} már fel van címkézve. Kihagyás.")
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
            with open(readme_path, 'r', encoding='utf-8') as f:
                # Csak az első 1500 karaktert küldjük el, hogy ne legyen lassú
                content = f.read()[:1500]

            prompt = f"""You are a librarian indexing Github repositories.
Read the following README excerpt and output a JSON object with exactly two keys:
1. "summary": A one-sentence description of what the project does.
2. "tags": An array of 3 short keyword strings (e.g. ["RAG", "Python", "CLI"]).

DO NOT output any other text, only the raw JSON format.

README excerpt:
{content}
"""
            response = query_local_ollama(prompt)

            # Tisztítás a JSON parse-hoz
            response = response.replace("```json", "").replace("```", "").strip()

            try:
                parsed = json.loads(response)
                labels[repo_name] = parsed
                print(f"✅ {repo_name} -> {parsed.get('tags', [])}")
            except json.JSONDecodeError:
                print(f"❌ JSON parse hiba a modell válaszánál ({repo_name}). Nyers válasz: {response[:50]}...")
                labels[repo_name] = {"summary": "Failed to parse LLM response", "tags": [], "raw": response[:100]}

        except Exception as e:
            print(f"Hiba a fájl olvasásakor: {e}")

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(labels, f, indent=4, ensure_ascii=False)
    print(f"🎉 Címkék elmentve: {OUTPUT_JSON}")

if __name__ == "__main__":
    # Ha van parancssori argumentum, csak azokat a mappákat dolgozza fel
    target_repos = sys.argv[1:] if len(sys.argv) > 1 else None
    process_repos(limit_to_dirs=target_repos)
