import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# 1. UI Színek Javítása: MCP Telemetria & Tool Hívások fejléc fehér betűkkel
old_header = '''                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>⚙️ MCP Telemetria & Tool Hívások</span>'''
new_header = '''                <div class="card-header d-flex justify-content-between align-items-center text-white">
                    <span>⚙️ MCP Telemetria & Tool Hívások</span>'''
content = content.replace(old_header, new_header)

# 2. UI Színek Javítása: Státusz és Részletek/Hiba oszlopok szürke háttéren jobban látható színekkel
# Részletek (Args) oszlop, ahol a "text-muted" túl sötét a sötétszürke háttéren. Cseréljük "text-light"-ra.
old_table_row = '''                        <td><small class="text-muted">${row.error || args.substring(0, 50)}</small></td>'''
new_table_row = '''                        <td><small class="text-light">${row.error || args.substring(0, 70)}</small></td>'''
content = content.replace(old_table_row, new_table_row)

# 3. Memória Épülés (Méret és Hossz) kijelzése az Agent Memory Stream panelen
old_memory_header = '''                <div class="card-header">
                    📖 Agent Memory Stream
                </div>'''
new_memory_header = '''                <div class="card-header d-flex justify-content-between align-items-center text-white">
                    <span>📖 Agent Memory Stream</span>
                    <span id="memory-stats" class="badge bg-primary">Méret: ...</span>
                </div>'''
content = content.replace(old_memory_header, new_memory_header)

# Memória JS update
old_js_mem = '''                // Memória stream
                const memBody = document.getElementById('memory-body');'''
new_js_mem = '''                // Memória stream
                document.getElementById('memory-stats').innerText = `Sorok: ${data.memory_stats.lines} | Méret: ${data.memory_stats.size_kb} KB`;
                const memBody = document.getElementById('memory-body');'''
content = content.replace(old_js_mem, new_js_mem)

# 4. Backend (Python API): Memória statisztikák és Ördög ügyvédje (Reflexiók) teljes frissítése
# Az előző API kódban a memória kinyerés (with open) nem olvasta be az ÚJ memória bejegyzéseket folyamatosan
# ha valami blokkolta, illetve a JSON API visszatérési értéket bővítjük a memstats-al
old_api_mem_fetch = '''    # 3. JSONL memória lekérése
    memory_entries = []
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines[-15:]):  # Utolsó 15 bejegyzés, legújabb elöl
                    try:
                        memory_entries.append(json.loads(line))
                    except:
                        pass
        except Exception as e:
            print("Memory hiba:", e)'''

new_api_mem_fetch = '''    # 3. JSONL memória lekérése
    memory_entries = []
    memory_stats = {"lines": 0, "size_kb": 0}
    if os.path.exists(MEMORY_PATH):
        try:
            size_kb = os.path.getsize(MEMORY_PATH) / 1024.0
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                memory_stats["lines"] = len(lines)
                memory_stats["size_kb"] = round(size_kb, 2)
                for line in reversed(lines[-15:]):  # Utolsó 15 bejegyzés, legújabb elöl
                    try:
                        memory_entries.append(json.loads(line))
                    except:
                        pass
        except Exception as e:
            print("Memory hiba:", e)'''
content = content.replace(old_api_mem_fetch, new_api_mem_fetch)

# Bővítjük a json return-t
old_json_ret = '''        "mcts_latest": mcts_latest if 'mcts_latest' in locals() else {},
        "graph_nodes": graph_nodes if 'graph_nodes' in locals() else [],
        "graph_edges": graph_edges if 'graph_edges' in locals() else []
    })'''
new_json_ret = '''        "mcts_latest": mcts_latest if 'mcts_latest' in locals() else {},
        "graph_nodes": graph_nodes if 'graph_nodes' in locals() else [],
        "graph_edges": graph_edges if 'graph_edges' in locals() else [],
        "memory_stats": memory_stats
    })'''
content = content.replace(old_json_ret, new_json_ret)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
