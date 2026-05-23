mcp_capabilities = """
Az ICA (Iterative Cognitive Architecture) rendszer és MCP eszköztára jelenleg az alábbi kulcsfunkciókat (Agent Skills) támogatja:

1. Kognitív Tervezés és Rendszer 2 (System 2) Gondolkodás:
   - deep_planning: Monte Carlo Tree Search (MCTS) és Tree of Thoughts alapú mély logikai tervező modul, amely az Ollama modellt (pl. qwen2.5:1.5b) használja a lehetséges jövőbeli állapotok és lépések szimulálására és értékelésére (reward based). Az MCTS Döntési Fa vizuálisan követhető a Web Monitorban (D3.js).

2. Rendszerfelügyelet és Megfigyelhetőség (Observability):
   - check_system_health: Diagnosztikai adatok lekérése a rendszerről.
   - ica_web_monitor.py: D3.js alapú vizuális Dashboard a 8080-as porton (Telemetria, Memória Stream, MCTS Gondolatfa és SQLite ICA Knowledge Graph megjelenítése).

3. Intelligens Memória és Tudásgráf (Knowledge Graph):
   - add_memory_node / add_memory_edge: Entitások és kapcsolatok hozzáadása a relációs ICA Tudásgráfhoz (SQLite - ica_knowledge_graph.db).
   - search_graph_fts: Villámgyors szöveges (Full-Text) keresés a gráfban.
   - search_graph_semantic: Vektoradatbázis (FAISS + SentenceTransformers) alapú szemantikus keresés a memóriában.
   - write_memory / read_memory_register: JSONL alapú esemény-memória írása, amely a Dashboardra is szinkronizálódik.
   - generate_core_memory_overview: Dinamikus kontextus-injektálás a routerből (System promptok frissítése).

4. Biztonság, Védvonalak (Guardrails) és Sandbox:
   - apply_guardrails: Zero-Trust ellenőrzés (AST szintaxis vizsgálat és Pydantic sémaellenőrzés).
   - write_file_mcp: Pipeline Gate - Csak akkor enged kódot menteni a VPS-re, ha a Guardrails validálta és létezik egy ADR (Architecture Decision Record) template alapján kitöltött blueprint.md.
   - execute_python: Bubblewrap (bwrap) alapú homokozóban, elszigetelt hálózattal és filerendszerrel futtat Python kódot.

5. Guerrilla RAG (Remote Retrieval-Augmented Generation) és Swarm Kommunikáció:
   - search_rag_database / search_rag_labels: Különböző elkülönített RAG SQLite adatbázisok (pl. BRAIN2_DEV, MQL5_Theory, video_downloader_RAG) lekérdezése az Ollama / RAG pipeline használatával.
   - create_swarm_job / get_next_swarm_job / complete_swarm_job: Fájl-alapú INBOX protokoll a multi-agent aszinkron kommunikációhoz (pl. Raj2 és Raj3 ügynökök közötti feladatkiosztás).

6. Külső és Lokális I/O:
   - github_list_user_repos / github_read_file: Külső GitHub repók olvasása dedikált SSH kulcsokkal.
   - fetch_webpage_mcp: Weboldalak szöveges tartalmának kinyerése.
   - execute_bash: Standard bash parancsok futtatása, a shell átirányítások (>, >>) biztonsági blokkolásával.
"""

import json

with open("agent_memory.jsonl", "a") as f:
    f.write(json.dumps({
        "timestamp": "2026-05-23T17:15:00",
        "category": "MCP_Capabilities_Overview",
        "content": mcp_capabilities
    }) + "\n")
