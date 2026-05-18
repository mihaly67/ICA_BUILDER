#!/usr/bin/env python3
import os
import sys
import json
import argparse
import subprocess

VPS_HOST = os.environ.get("VPS_HOST", "5.189.163.88")
VPS_USER = os.environ.get("VPS_USER", "misi")

def search_repo_labels(query):
    """
    Ez az eszköz MCP hívásokat emulál a VPS felé:
    Rácsatlakozik a VPS RAG adatbázisára, beolvassa a REPO_LABELS.json fájlt,
    és szemantikus/kulcsszavas keresést hajt végre rajta.
    Így az LLM azonnal látja a sekély előfeldolgozás eredményeit.
    """
    target_json = "/home/misi/Rag_epites, chatbot_csv_data_llm_RAG/REPO_LABELS.json"

    # 1. Lekérdezzük a JSON fájlt a VPS-ről 'cat' paranccsal
    cmd = f"cat '{target_json}'"
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{VPS_USER}@{VPS_HOST}", cmd]

    env = os.environ.copy()
    vps_pwd = os.environ.get("VPS_PWD")
    if vps_pwd:
        ssh_cmd = ["sshpass", "-e"] + ssh_cmd
        env["SSHPASS"] = vps_pwd

    try:
        result = subprocess.run(ssh_cmd, check=True, capture_output=True, text=True, env=env)
        labels_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return f"Hiba az SSH hívás során: A REPO_LABELS.json valószínűleg nem létezik vagy a VPS nem elérhető."
    except json.JSONDecodeError:
        return f"Hiba: A VPS-ről érkező JSON érvénytelen."

    # 2. Egyszerű kisbetűs keresés a címkékben és az összefoglalókban
    query_lower = query.lower()
    matches = []

    for repo, data in labels_data.items():
        summary = data.get("summary", "")
        tags = data.get("tags", [])

        # Ha a keresőszó benne van a repó nevében, a summary-ben, vagy a tag-ek között
        if (query_lower in repo.lower() or
            query_lower in summary.lower() or
            any(query_lower in t.lower() for t in tags)):
            matches.append({
                "repo": repo,
                "summary": summary,
                "tags": tags
            })

    # 3. Formázott válasz
    if not matches:
        return f"Nincs találat a RAG Adatbázisban a következőre: '{query}'."

    output = f"🔍 Keresési eredmények a RAG Adatbázisban ('{query}'):\n\n"
    for m in matches:
        output += f"📁 Repó: {m['repo']}\n"
        output += f"   📝 {m['summary']}\n"
        output += f"   🏷️ Címkék: {', '.join(m['tags'])}\n"
        output += "-" * 40 + "\n"

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VPS Repo Label Kereső Eszköz (MCP Emuláció)")
    parser.add_argument("query", type=str, help="A keresendő kulcsszó (pl. 'RAG', 'Agent', 'Memory')")
    args = parser.parse_args()

    print(search_repo_labels(args.query))
