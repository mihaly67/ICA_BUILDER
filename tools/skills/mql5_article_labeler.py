#!/usr/bin/env python3
import os
import json
import sqlite3
import re
import urllib.request

# This script is a draft for extracting summaries and tags from the MQL5 articles RAG DB.
# It is designed to run locally on the VPS and read from `mql5_articles_brain2dev.db`.
# It targets article HTML contents (which contain embedded `.mq5` codebase sections).

DB_PATH = "/home/misi/MQL5_Theory/mql5_articles_brain2dev.db"
OUTPUT_JSON = "/home/misi/MQL5_Theory/ARTICLE_LABELS.json"
MODEL = "llama3:latest"

def query_local_ollama(prompt):
    url = "http://localhost:11434/api/generate"
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
    try:
        return json.loads(response_text)
    except:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    return None

def process_articles():
    labels = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
                labels = json.load(f)
        except:
            pass

    print(f"🔍 Articles scanning from: {DB_PATH}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all distinct articles. In this DB, files are saved directly as article_XXX.html.
        cursor.execute("SELECT filepath, content FROM rag_data WHERE filepath LIKE '%.html'")
        rows = cursor.fetchall()

        for row in rows:
            filepath, content = row

            if filepath in labels and "Failed" not in labels[filepath].get("summary", ""):
                print(f"⏭️ {filepath} already labeled. Skipping.")
                continue

            # Extract the beginning of the article to give the LLM context of what it's about
            # And also try to extract any attached code filenames to list them as well.
            header_content = content[:2500]

            code_files = re.findall(r'====== File: (.*?) ======', content)
            code_summary = ""
            if code_files:
                code_summary = "\nThis article includes attached source codes: " + ", ".join(code_files)

            prompt = f"""You are an expert MQL5 algorithmic trading developer.
Analyze the following MQL5 article excerpt. Output a valid JSON object with exactly these keys:
"title": Try to guess a concise title or topic for the article based on the text.
"summary": A concise one-sentence description of the main MQL5 concept discussed.
"tags": An array of exactly 3 relevant technical keywords (e.g., ["MQL5", "Indicators", "Neural Networks"]).

ARTICLE EXCERPT:
{header_content}
{code_summary}
"""
            print(f"🧠 Processing {filepath} with {MODEL}...")
            response = query_local_ollama(prompt)
            parsed = extract_json(response)

            if parsed and "summary" in parsed and "tags" in parsed:
                # Store any associated files extracted via Regex alongside the LLM data
                if code_files:
                    parsed["attached_files"] = code_files

                labels[filepath] = parsed
                print(f"✅ SUCCESS: {filepath} -> {parsed.get('tags', [])}")
            else:
                print(f"❌ JSON parse error for {filepath}.")
                labels[filepath] = {"summary": "Failed to parse LLM response", "tags": []}

            # Save incrementally
            with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
                json.dump(labels, f, indent=4, ensure_ascii=False)

        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

    print(f"🎉 Processing complete. Labels saved to: {OUTPUT_JSON}")

if __name__ == "__main__":
    # WARNING: Do not run locally. This is designed for the VPS environment.
    print("Draft generated. Use SCP to push to VPS and run there.")
