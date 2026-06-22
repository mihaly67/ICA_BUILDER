import os
import json
import sqlite3
import time
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import re

logging.basicConfig(filename='graph_builder.log', level=logging.INFO, format='%(asctime)s - %(message)s')

MEMORY_PATH = "/home/misi/Jules_ICA_Builder/Knowledge_Base/agent_memory.jsonl"
GRAPH_DB_PATH = "/home/misi/Jules_ICA_Builder/ica_knowledge_graph.db"

def init_graph_db():
    conn = sqlite3.connect(GRAPH_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            type TEXT,
            description TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            target_id INTEGER,
            relationship TEXT,
            weight REAL DEFAULT 1.0,
            FOREIGN KEY(source_id) REFERENCES entities(id),
            FOREIGN KEY(target_id) REFERENCES entities(id),
            UNIQUE(source_id, target_id, relationship)
        )
    ''')
    conn.commit()
    conn.close()

def build_graph_from_memory():
    if not os.path.exists(MEMORY_PATH):
        return

    try:
        conn = sqlite3.connect(GRAPH_DB_PATH)
        c = conn.cursor()

        with open(MEMORY_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_nodes = 0
        new_edges = 0

        # Mentsük el a korábbi node-okat egy listába, hogy összeköthessük a kronológiát
        previous_node_id = None

        for line in lines:
            if not line.strip(): continue
            try:
                mem = json.loads(line)
                cat = mem.get('category', '')
                content = mem.get('content', '')

                # Csak a fontos mérföldköveket / sarokköveket tesszük be a gráfba
                if cat in ['Architecture_Decision', 'Reflection', 'Context_Summary', 'Session_Handoff'] and content:

                    # Generálunk egy beszédes, rövid nevet a node-nak a kategóriából és az időbélyegből
                    timestamp = mem.get('timestamp', '')
                    short_ts = timestamp.split('T')[0] if timestamp else "unknown_date"

                    # Szavak kinyerése a contentből
                    words = re.findall(r'\b[a-zA-Z]{5,15}\b', content)
                    key_words = "_".join(words[:2]) if words else "Memory"

                    name = f"Mem_{cat}_{short_ts}_{key_words}"

                    # 1. NODE HOZZÁADÁSA
                    c.execute("INSERT OR IGNORE INTO entities (name, type, description) VALUES (?, ?, ?)",
                              (name, "memory_milestone", content))

                    # Lekérjük az ID-t
                    c.execute("SELECT id FROM entities WHERE name = ?", (name,))
                    row = c.fetchone()
                    if not row: continue
                    current_node_id = row[0]

                    # Ha ez egy új node, növeljük a számlálót
                    if c.rowcount > 0:
                        new_nodes += 1

                    # 2. CHRONOLÓGIAI EDGE (VONAL) HÚZÁSA AZ ELŐZŐHÖZ
                    if previous_node_id is not None and previous_node_id != current_node_id:
                        try:
                            c.execute("INSERT INTO edges (source_id, target_id, relationship) VALUES (?, ?, ?)",
                                      (previous_node_id, current_node_id, "followed_by"))
                            new_edges += 1
                        except sqlite3.IntegrityError:
                            pass # Már létezik a kapcsolat

                    previous_node_id = current_node_id

            except json.JSONDecodeError:
                pass

        conn.commit()
        if new_nodes > 0 or new_edges > 0:
            logging.info(f"Hozzáadva {new_nodes} új sarokkő (node) és {new_edges} új kronológiai kapcsolat (edge) a Tudásgráfhoz a memóriából.")
    except Exception as e:
        logging.error(f"Hiba a gráf építésekor: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    init_graph_db()
    print("Indítom a VPS Tudásgráf Építő Szolgáltatást (10 percenként)...")
    build_graph_from_memory()
    scheduler = BackgroundScheduler()
    scheduler.add_job(build_graph_from_memory, 'interval', minutes=10)
    scheduler.start()

    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
