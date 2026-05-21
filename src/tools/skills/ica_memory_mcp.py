#!/usr/bin/env python3
"""
Jules ICA - Knowledge Graph Memória Modul
Ez a modul egy relációs SQLite adatbázisra építve tárolja az architektúra elemeit,
így az AI térképszerű (gráf) kontextust kaphat a projekt struktúrájáról.
"""
import sys
import json
import os
import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Jules-Memory-Graph-Module")

GRAPH_DB_PATH = os.path.expanduser("~/Jules_ICA_Builder/ica_knowledge_graph.db")

def init_graph_db():
    os.makedirs(os.path.dirname(GRAPH_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(GRAPH_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS entities (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, type TEXT NOT NULL, description TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS edges (id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER NOT NULL, target_id INTEGER NOT NULL, relationship TEXT NOT NULL, FOREIGN KEY (source_id) REFERENCES entities(id), FOREIGN KEY (target_id) REFERENCES entities(id), UNIQUE(source_id, target_id, relationship))')
    cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(id UNINDEXED, name, description, content='entities', content_rowid='id');")
    cursor.execute("CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN INSERT INTO entities_fts(rowid, name, description) VALUES (new.id, new.name, new.description); END;")
    cursor.execute("CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN INSERT INTO entities_fts(entities_fts, rowid, name, description) VALUES('delete', old.id, old.name, old.description); END;")
    cursor.execute("CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN INSERT INTO entities_fts(entities_fts, rowid, name, description) VALUES('delete', old.id, old.name, old.description); INSERT INTO entities_fts(rowid, name, description) VALUES (new.id, new.name, new.description); END;")
    conn.commit()
    conn.close()


@mcp.tool()
def add_memory_node(name: str, entity_type: str, description: str) -> str:
    init_graph_db()
    try:
        conn = sqlite3.connect(GRAPH_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO entities (name, type, description) VALUES (?, ?, ?)", (name, entity_type, description))
        node_id = cursor.lastrowid
        conn.commit()
        conn.close()

        try:
            get_faiss_mem().add_node(node_id, name, description)
        except Exception as fe:
            pass

        return f"✅ Entitás '{name}' ({entity_type}) sikeresen a Gráfba mentve."
    except Exception as e:
        return f"Hiba a node mentésekor: {e}"
@mcp.tool()
def add_memory_edge(source_name: str, target_name: str, relationship: str) -> str:
    """
    Hozzáad egy Kapcsolatot (Élt) két meglévő Entitás között.
    Pl: source_name="ica_mcp_router.py", target_name="ica_guardrails_mcp.py", relationship="depends_on"
    """
    init_graph_db()
    try:
        conn = sqlite3.connect(GRAPH_DB_PATH)
        cursor = conn.cursor()

        # Ellenőrizzük, hogy léteznek-e a csomópontok
        cursor.execute("SELECT id FROM entities WHERE name = ?", (source_name,))
        src = cursor.fetchone()
        cursor.execute("SELECT id FROM entities WHERE name = ?", (target_name,))
        tgt = cursor.fetchone()

        if not src or not tgt:
            conn.close()
            return f"🚨 Hiba: A forrás ('{source_name}') vagy a cél ('{target_name}') entitás még nem létezik a gráfban! Előbb használd az add_memory_node-ot."

        cursor.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relationship) VALUES (?, ?, ?)",
                       (src[0], tgt[0], relationship))
        conn.commit()
        conn.close()
        return f"✅ Kapcsolat létrehozva: [{source_name}] --({relationship})--> [{target_name}]"
    except Exception as e:
        return f"Hiba a kapcsolat mentésekor: {e}"

@mcp.tool()
def query_graph_context(topic_name: str) -> str:
    """
    Lekérdezi a Tudásgráfot egy adott entitásról, és visszaadja a hozzá kapcsolódó teljes hálózatot.
    Használd kódolás előtt a teljes kontextus megértéséhez!
    """
    init_graph_db()
    try:
        conn = sqlite3.connect(GRAPH_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id, type, description FROM entities WHERE name = ?", (topic_name,))
        entity = cursor.fetchone()

        if not entity:
            conn.close()
            return f"A '{topic_name}' entitás nem található a gráfban."

        entity_id, e_type, e_desc = entity

        output = [f"🌐 GRÁF KONTEXTUS: [{topic_name}] ({e_type})"]
        output.append(f"Leírás: {e_desc}\n")
        output.append("Kimenő kapcsolatok:")

        cursor.execute('''
            SELECT relationship, e.name
            FROM edges
            JOIN entities e ON edges.target_id = e.id
            WHERE source_id = ?
        ''', (entity_id,))
        for rel, target in cursor.fetchall():
            output.append(f"  --({rel})--> [{target}]")

        output.append("\nBejövő kapcsolatok:")
        cursor.execute('''
            SELECT e.name, relationship
            FROM edges
            JOIN entities e ON edges.source_id = e.id
            WHERE target_id = ?
        ''', (entity_id,))
        for source, rel in cursor.fetchall():
            output.append(f"  [{source}] --({rel})-->")

        conn.close()
        return "\n".join(output)
    except Exception as e:
        return f"Hiba a lekérdezéskor: {e}"


@mcp.tool()
def generate_core_memory_overview() -> str:
    """
    A MemGPT logikája alapján legenerál egy Core Memory kivonatot a JSONL és a GraphRAG alapján.
    Ezt a router automatikusan injektálja az AI System Promptjába, elkerülve a végtelen chat historyt.
    """
    import os

    output = ["--- ICA CORE MEMORY (WORKING CONTEXT) ---"]

    # 1. GraphRAG összefoglaló (Aktív csomópontok)
    init_graph_db()
    try:
        conn = sqlite3.connect(GRAPH_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name, type FROM entities ORDER BY id DESC LIMIT 5")
        recent_nodes = cursor.fetchall()
        conn.close()

        output.append("📌 Legutóbb használt Architektúra Elemek (Graph Nodes):")
        if recent_nodes:
            for name, e_type in recent_nodes:
                output.append(f"  - [{name}] ({e_type})")
        else:
            output.append("  (A gráf még üres)")
    except Exception as e:
         output.append(f"⚠️ Hiba a gráf olvasásakor: {e}")

    # 2. Archival Memory (JSONL) Pointers
    target_dir = "/home/misi/Jules_ICA_Builder"
    memory_file = os.path.join(target_dir, "agent_memory.jsonl")

    output.append("\n🧠 Hosszútávú Memória Mutatók (Archival Memory):")
    if os.path.exists(memory_file):
        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                total_memories = len(lines)
                output.append(f"  Összes memória bejegyzés: {total_memories} db. (Ha részletek kellenek, használd a `get_memory` eszközt!)")

                # Csak az utolsó 1 bejegyzés címét mutatjuk
                if total_memories > 0:
                    import json
                    last_obj = json.loads(lines[-1])
                    output.append(f"  Legutóbbi bejegyzés témája: {last_obj.get('category', 'Ismeretlen')} ({last_obj.get('timestamp', '')})")
        except Exception as e:
            output.append(f"⚠️ Hiba a JSONL olvasásakor: {e}")
    else:
        output.append("  (A jsonl memória még üres)")

    output.append("-------------------------------------------")
    return "\n".join(output)

if __name__ == "__main__":
    mcp.run()


import ica_faiss_memory
global_faiss_mem = None

def get_faiss_mem():
    global global_faiss_mem
    if global_faiss_mem is None:
        global_faiss_mem = ica_faiss_memory.FAISSGraphMemory()
    return global_faiss_mem

@mcp.tool()
def search_graph_semantic(query: str, limit: int = 5) -> str:
    try:
        results = get_faiss_mem().search(query, top_k=limit)
        import json
        return json.dumps(results)
    except Exception as e:
        return f"Hiba a FAISS keresés során: {e}"
@mcp.tool()
def search_graph_fts(query: str, limit: int = 5) -> str:
    try:
        conn = sqlite3.connect('/home/misi/Jules_ICA_Builder/ica_knowledge_graph.db')
        c = conn.cursor()
        c.execute("SELECT name, description FROM entities_fts WHERE entities_fts MATCH ? ORDER BY rank LIMIT ?", (query, limit))
        results = c.fetchall()
        conn.close()
        import json
        return json.dumps([{"name": r[0], "description": r[1]} for r in results])
    except Exception as e:
        return f"Hiba az FTS5 keresés során: {e}"
