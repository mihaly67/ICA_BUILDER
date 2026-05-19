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
    """Létrehozza a gráf adatbázis tábláit, ha nem léteznek."""
    os.makedirs(os.path.dirname(GRAPH_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(GRAPH_DB_PATH)
    cursor = conn.cursor()

    # Entitások (Csomópontok / Nodes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            description TEXT
        )
    ''')

    # Kapcsolatok (Élek / Edges)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            relationship TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES entities(id),
            FOREIGN KEY (target_id) REFERENCES entities(id),
            UNIQUE(source_id, target_id, relationship)
        )
    ''')
    conn.commit()
    conn.close()

@mcp.tool()
def add_memory_node(name: str, entity_type: str, description: str) -> str:
    """
    Hozzáad egy Entitást (Csomópontot) a Tudásgráfhoz.
    Pl: name="ica_mcp_router.py", type="File", description="Központi MCP gateway."
    """
    init_graph_db()
    try:
        conn = sqlite3.connect(GRAPH_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO entities (name, type, description) VALUES (?, ?, ?)",
                       (name, entity_type, description))
        conn.commit()
        conn.close()
        return f"✅ Entitás '{name}' ({entity_type}) sikeresen a Gráfba mentve."
    except Exception as e:
        return f"Hiba az entitás mentésekor: {e}"

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

if __name__ == "__main__":
    mcp.run()
