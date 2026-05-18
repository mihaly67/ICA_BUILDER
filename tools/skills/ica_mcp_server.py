#!/usr/bin/env python3
"""
Jules ICA - Központi MCP Szerver
Ez a fájl fut a VPS-en (vagy a lokál gépen), és az összes eddigi eszközt (tools),
kognitív protokollt és RAG adatbázis hivatkozást "becsövezi" egy szabványos MCP felületbe.
A következő Jules sessionnek elég csak ehhez az EGY szerverhez csatlakoznia.
"""
import sys
import json
import os
from mcp.server.fastmcp import FastMCP

# Konfiguráció
TARGET_DIR = "/home/misi/Jules_ICA_Builder"
RAG_PATH = "/home/misi/Rag_epites, chatbot_csv_data_llm_RAG/"
MEMORY_FILE = os.path.join(TARGET_DIR, "agent_memory.jsonl")

# MCP Szerver Inicializálása
mcp = FastMCP("Jules-ICA-Cognitive-Engine")

@mcp.tool()
def read_system_protocols() -> str:
    """Visszaadja a kötelező viselkedési szabályokat és protokollokat az ICA Agent számára."""
    protocol = (
        "1. IDENTITÁS: Jules ICA Builder vagy. Nem rajtag.\n"
        "2. SILENT MODE: A Kognitív Ciklust belsőleg fusd le, de csak '[KOGNITÍV CIKLUS LEFUTOTT]' formában jelezd.\n"
        "3. KÖZPONTI RAG: Minden tudás a " + RAG_PATH + " mappában van.\n"
    )
    return protocol

@mcp.tool()
def get_memory(lines: int = 10) -> str:
    """Beolvassa az agent hosszú távú JSONL memóriáját, hogy tudja, mi történt korábban."""
    if not os.path.exists(MEMORY_FILE):
        return "Nincs elérhető memória."
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception as e:
        return f"Hiba a memória olvasásakor: {e}"

@mcp.tool()
def write_memory(category: str, content: str) -> str:
    """Beleír egy új bejegyzést a JSONL memóriába."""
    import datetime
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "category": category,
        "content": content
    }
    try:
        with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
        return "Memória sikeresen mentve."
    except Exception as e:
        return f"Hiba a mentésnél: {e}"

@mcp.tool()
def search_rag_labels(query: str) -> str:
    """Keres az előre felcímkézett (Llama által processzált) RAG repók között."""
    label_file = os.path.join(RAG_PATH, "REPO_LABELS.json")
    if not os.path.exists(label_file):
        return "Nincs REPO_LABELS.json a VPS-en."
    try:
        with open(label_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        query_lower = query.lower()
        matches = []
        for repo, info in data.items():
            if query_lower in repo.lower() or query_lower in info.get("summary", "").lower():
                matches.append(f"Repo: {repo} | Summary: {info.get('summary')}")

        if not matches:
            return "Nincs találat."
        return "\n".join(matches)
    except Exception as e:
        return f"Keresési hiba: {e}"

if __name__ == "__main__":
    # MCP standard IO szerver indítása
    mcp.run()
