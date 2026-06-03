#!/usr/bin/env python3
"""
Jules ICA - MCP Router (Decentralizált Gateway)
Mivel az mcp_server.py kódja egyre hosszabb, ez a Router script
több MCP szervert integrál egybe a tool() metódus dinamikus hívásával.
"""
import sys
import os
import inspect

import time
import inspect
from mcp.server.fastmcp import FastMCP

import ica_telemetry




def cognitive_preflight_check(func_name, kwargs):
    """
    Fizikai kényszerítő kapu (Pipeline Gate) a rendszerműködtetéshez.
    Bizonyos kritikus MCP eszközök (pl. fájlírás) hívásakor az LLM-nek
    bizonyítania kell, hogy reflektált a szabályokra.
    """
    critical_tools = ["write_file_mcp", "execute_bash"]
    if func_name in critical_tools:
        # Ha a tool megengedi a 'justification' vagy 'reasoning' mezőt
        justification = kwargs.get("justification", kwargs.get("reasoning", ""))

        if not justification or len(str(justification)) < 20:
            raise ValueError(f"Cognitive Pre-flight Check ELBUKOTT! A '{func_name}' eszköz használatához "
                             f"kötelező megadni egy részletes 'justification' vagy 'reasoning' paramétert (>20 karakter), "
                             f"amelyben megindokolod, hogy a lépés hogyan illeszkedik az AGENTS_ICA.md és a Zero Trust szabályrendszerbe.")

        # Ide jöhetne később akár egy LLM alapú (pl. Ollama) validáció is a megadott reasoning-re,
        # de a "Münchhausen" problémát elkerülendő, már maga a strukturális kényszerítés (hogy ki kell tölteni) is rákényszeríti az Agentet a System 2 gondolkodásra.


def add_tool_with_telemetry(func):
    # Ezzel elkerüljük az async paraméter-vizsgálat (signature) problémákat,
    # de egyelőre a legegyszerűbb, ha beállítjuk a wrapperre az eredeti signaturat
    import functools
    @functools.wraps(func)
    async def async_wrapped(*args, **kwargs):
        start = time.time()

        try:
            cognitive_preflight_check(func.__name__, kwargs)
        except Exception as preflight_err:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(preflight_err))

            # Kényszerített Reflexió (Auto-Critique)
            try:
                import json
                import datetime
                err_msg = str(preflight_err).replace('"', "'")
                critique = f"Auto-Reflexió (Pre-flight): {err_msg}. Elfelejtettem a rendszerműködtetési kereteket igazolni!"
                with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
                    mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\n")
            except:
                pass
            raise preflight_err

        try:
            res = await func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000

            mcts_data = None
            if func.__name__ == "deep_planning" and isinstance(res, str):
                import json
                try:
                    res_dict = json.loads(res)
                    if "tree_data" in res_dict:
                        mcts_data = res_dict["tree_data"]

                    # --- AUTO-GRAPH COMMITTER ---
                    # Ha a deep_planning sikeresen lefutott, kimentjük a végkövetkeztetést a memóriába és a Tudásgráfba
                    best_action = res_dict.get("best_action", "")
                    best_value = res_dict.get("best_value", 0.0)
                    if best_action:
                        # 1. Beírás az agent_memory.jsonl-be
                        import datetime
                        try:
                            # A 'get_budapest_2026_time' logikáját szimuláljuk (vagy használjuk az alapértelmezett ISO formátumot)
                            timestamp = datetime.datetime.now().isoformat()
                            if "2026-" not in timestamp:
                                timestamp = timestamp.replace(str(datetime.datetime.now().year), "2026")

                            memory_entry = {
                                "timestamp": timestamp,
                                "category": "MCTS_Auto_Committer",
                                "content": f"System 2 (Deep Planning) automatikus következtetése: '{best_action}' (Bizonyosság: {best_value})"
                            }
                            # Mivel az mcp_telemetry is a /home/misi/... helyen van elvárva,
                            # biztonsági okokból használjuk az agent_memory fájlt. (ha lokális dockerben van, ott a fájl elérhető az ENVIRONMENT_SETUP/ alapján is)
                            mem_file_paths = [
                                "/home/misi/Jules_ICA_Builder/Knowledge_Base/agent_memory.jsonl",
                                "/home/misi/Jules_ICA_Builder/agent_memory.jsonl",
                                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "Knowledge_Base", "agent_memory.jsonl")
                            ]
                            for mem_path in mem_file_paths:
                                if os.path.exists(os.path.dirname(mem_path)):
                                    with open(mem_path, "a", encoding="utf-8") as mem_f:
                                        mem_f.write(json.dumps(memory_entry) + "\n")
                                    break
                        except Exception as e:
                            print(f"Auto-Graph Committer Memory Error: {e}")
                            pass

                        # 2. Beírás az ICA Tudásgráfba (Entities és Edges)
                        try:
                            import ica_memory_mcp
                            # Node hozzáadása
                            node_name = f"MCTS_Plan_{int(time.time())}"
                            ica_memory_mcp.add_memory_node(
                                name=node_name,
                                entity_type="System2_Thought",
                                description=f"Automatikusan generált MCTS Deep Planning eredmény: {best_action}"
                            )
                            # Kapcsolat hozzáadása egy Core elemhez, pl 'ICA Builder'
                            ica_memory_mcp.add_memory_edge(
                                source_name=node_name,
                                target_name="ICA Builder",
                                relationship="planned_by",
                                weight=float(best_value)
                            )
                        except Exception as e:
                            print(f"Auto-Graph Committer Graph Error: {e}")
                            pass
                    # --- AUTO-GRAPH COMMITTER END ---
                except:
                    pass

            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success", mcts_data=mcts_data)

            # ---------------------------------------------------------
            # FOLYAMATOS MEMÓRIA MENTÉS - ÚJ FUNKCIÓ
            # ---------------------------------------------------------
            # Mivel a felhasználó azt kérte, hogy a jsonl fájl automatikusan is frissüljön idővel (ha van változás)
            # vagy ne legyen információvesztés: a kritikus tool hívások (mint pl. file írás, shell parancs, stb) után
            # egy "Activity Marker" kerül a memóriába (ha régen volt már mentés).
            try:
                if func.__name__ in ["execute_bash", "write_file_mcp", "add_memory_node", "add_memory_edge"]:
                    import time
                    import json
                    import datetime

                    last_activity_time = getattr(router_mcp, "_last_auto_memory_time", 0)
                    current_time = time.time()

                    # Csak 1 percenként írjunk be automatikusan, hogy ne floodoljuk szét a Stream-et
                    if current_time - last_activity_time > 60:
                        router_mcp._last_auto_memory_time = current_time

                        timestamp = datetime.datetime.now().isoformat()
                        if "2026-" not in timestamp:
                            timestamp = timestamp.replace(str(datetime.datetime.now().year), "2026")

                        # Szimuláljuk a "Memory Summary"-t vagy csak rögzítünk egy automatikus checkpointot.
                        memory_entry = {
                            "timestamp": timestamp,
                            "category": "Auto_Activity_Checkpoint",
                            "content": f"A rendszer aktívan használta a(z) '{func.__name__}' eszközt. Állapot/Kontextus megőrizve."
                        }

                        mem_file_paths = [
                            "/home/misi/Jules_ICA_Builder/Knowledge_Base/agent_memory.jsonl",
                            "/home/misi/Jules_ICA_Builder/agent_memory.jsonl",
                            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "Knowledge_Base", "agent_memory.jsonl")
                        ]
                        for mem_path in mem_file_paths:
                            if os.path.exists(os.path.dirname(mem_path)):
                                with open(mem_path, "a", encoding="utf-8") as mem_f:
                                    mem_f.write(json.dumps(memory_entry) + "\n")
                                break
            except Exception as e:
                pass
            # ---------------------------------------------------------

            return res
        except Exception as e:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e))

            # AUTO-CRITIQUE TRIGGER
            try:
                import json
                import datetime
                err_msg = str(e).replace('"', "'")
                critique = f"Auto-Reflexió: A '{func.__name__}' eszköz hibára futott. Ok: {err_msg}. Az Agentnek felül kell vizsgálnia a stratégiát, mert valószínűleg megsértett egy Guardrailt vagy hibás argumentumokat adott át."
                with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
                    mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\n")
            except:
                pass

            raise e

    @functools.wraps(func)
    def sync_wrapped(*args, **kwargs):
        start = time.time()

        try:
            cognitive_preflight_check(func.__name__, kwargs)
        except Exception as preflight_err:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(preflight_err))

            # Kényszerített Reflexió (Auto-Critique)
            try:
                import json
                import datetime
                err_msg = str(preflight_err).replace('"', "'")
                critique = f"Auto-Reflexió (Pre-flight): {err_msg}. Elfelejtettem a rendszerműködtetési kereteket igazolni!"
                with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
                    mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\n")
            except:
                pass
            raise preflight_err

        try:
            res = func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000

            mcts_data = None
            if func.__name__ == "deep_planning" and isinstance(res, str):
                import json
                try:
                    res_dict = json.loads(res)
                    if "tree_data" in res_dict:
                        mcts_data = res_dict["tree_data"]

                    # --- AUTO-GRAPH COMMITTER ---
                    # Ha a deep_planning sikeresen lefutott, kimentjük a végkövetkeztetést a memóriába és a Tudásgráfba
                    best_action = res_dict.get("best_action", "")
                    best_value = res_dict.get("best_value", 0.0)
                    if best_action:
                        # 1. Beírás az agent_memory.jsonl-be
                        import datetime
                        try:
                            # A 'get_budapest_2026_time' logikáját szimuláljuk (vagy használjuk az alapértelmezett ISO formátumot)
                            timestamp = datetime.datetime.now().isoformat()
                            if "2026-" not in timestamp:
                                timestamp = timestamp.replace(str(datetime.datetime.now().year), "2026")

                            memory_entry = {
                                "timestamp": timestamp,
                                "category": "MCTS_Auto_Committer",
                                "content": f"System 2 (Deep Planning) automatikus következtetése: '{best_action}' (Bizonyosság: {best_value})"
                            }
                            # Mivel az mcp_telemetry is a /home/misi/... helyen van elvárva,
                            # biztonsági okokból használjuk az agent_memory fájlt.
                            mem_file_paths = [
                                "/home/misi/Jules_ICA_Builder/Knowledge_Base/agent_memory.jsonl",
                                "/home/misi/Jules_ICA_Builder/agent_memory.jsonl",
                                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "Knowledge_Base", "agent_memory.jsonl")
                            ]
                            for mem_path in mem_file_paths:
                                if os.path.exists(os.path.dirname(mem_path)):
                                    with open(mem_path, "a", encoding="utf-8") as mem_f:
                                        mem_f.write(json.dumps(memory_entry) + "\n")
                                    break
                        except Exception as e:
                            print(f"Auto-Graph Committer Memory Error: {e}")
                            pass

                        # 2. Beírás az ICA Tudásgráfba (Entities és Edges)
                        try:
                            import ica_memory_mcp
                            # Először ellenőrizzük, létezik-e az 'ICA Builder' node (hogy ne kapjunk errort az edge-nél)
                            ica_memory_mcp.add_memory_node(
                                name="ICA Builder",
                                entity_type="System",
                                description="A központi ICA Builder rendszer (Core)."
                            )
                            # Node hozzáadása
                            node_name = f"MCTS_Plan_{int(time.time())}"
                            ica_memory_mcp.add_memory_node(
                                name=node_name,
                                entity_type="System2_Thought",
                                description=f"Automatikusan generált MCTS Deep Planning eredmény: {best_action}"
                            )
                            # Kapcsolat hozzáadása a Core elemhez
                            ica_memory_mcp.add_memory_edge(
                                source_name=node_name,
                                target_name="ICA Builder",
                                relationship="planned_by",
                                weight=float(best_value)
                            )
                        except Exception as e:
                            print(f"Auto-Graph Committer Graph Error: {e}")
                            pass
                    # --- AUTO-GRAPH COMMITTER END ---
                except:
                    pass

            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success", mcts_data=mcts_data)

            # ---------------------------------------------------------
            # FOLYAMATOS MEMÓRIA MENTÉS - ÚJ FUNKCIÓ (SYNC WRAPPED)
            # ---------------------------------------------------------
            try:
                if func.__name__ in ["execute_bash", "write_file_mcp", "add_memory_node", "add_memory_edge"]:
                    import time
                    import json
                    import datetime

                    last_activity_time = getattr(router_mcp, "_last_auto_memory_time_sync", 0)
                    current_time = time.time()

                    if current_time - last_activity_time > 60:
                        router_mcp._last_auto_memory_time_sync = current_time

                        timestamp = datetime.datetime.now().isoformat()
                        if "2026-" not in timestamp:
                            timestamp = timestamp.replace(str(datetime.datetime.now().year), "2026")

                        memory_entry = {
                            "timestamp": timestamp,
                            "category": "Auto_Activity_Checkpoint",
                            "content": f"A rendszer aktívan használta a(z) '{func.__name__}' eszközt. Állapot/Kontextus megőrizve."
                        }

                        mem_file_paths = [
                            "/home/misi/Jules_ICA_Builder/Knowledge_Base/agent_memory.jsonl",
                            "/home/misi/Jules_ICA_Builder/agent_memory.jsonl",
                            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "Knowledge_Base", "agent_memory.jsonl")
                        ]
                        for mem_path in mem_file_paths:
                            if os.path.exists(os.path.dirname(mem_path)):
                                with open(mem_path, "a", encoding="utf-8") as mem_f:
                                    mem_f.write(json.dumps(memory_entry) + "\n")
                                break
            except Exception as e:
                pass
            # ---------------------------------------------------------

            return res
        except Exception as e:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e))

            # AUTO-CRITIQUE TRIGGER
            try:
                import json
                import datetime
                err_msg = str(e).replace('"', "'")
                critique = f"Auto-Reflexió: A '{func.__name__}' eszköz hibára futott. Ok: {err_msg}. Az Agentnek felül kell vizsgálnia a stratégiát, mert valószínűleg megsértett egy Guardrailt vagy hibás argumentumokat adott át."
                with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
                    mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\n")
            except:
                pass

            raise e

    wrapped = async_wrapped if inspect.iscoroutinefunction(func) else sync_wrapped
    router_mcp.tool()(wrapped)


current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import ica_mcp_server as io_server
import ica_guardrails_mcp as guardrails_server
import ica_memory_mcp as memory_server

# Inbox olvasása és Dinamikus Core Memory (Event-Driven Reminder Injection)
inbox_alerts = []
try:
    inbox_dir = "/home/misi/Jules_mx/temp/inbox"
    if os.path.exists(inbox_dir):
        for filename in os.listdir(inbox_dir):
            if filename.startswith("msg_") and filename.endswith(".txt"):
                filepath = os.path.join(inbox_dir, filename)
                with open(filepath, "r", encoding="utf-8") as inf:
                    inbox_alerts.append(inf.read())
                # # os.remove(filepath) - Letiltva a code-review alapján, hogy ne töröljön inbox fájlokat - Letiltva a code-review alapján, hogy ne töröljön inbox fájlokat
except Exception as e:
    inbox_alerts.append(f"⚠️ Inbox olvasási hiba: {e}")

inbox_context = ""
if inbox_alerts:
    inbox_context = "\n🚨 [FONTOS RENDSZERÜZENET / INBOX] 🚨\n" + "\n---\n".join(inbox_alerts) + "\n(A fenti üzeneteket vedd figyelembe a válaszodban!)\n"

try:
    core_memory_context = memory_server.generate_core_memory_overview()
except Exception as e:
    core_memory_context = f"⚠️ Core Memory nem elérhető: {e}"

system_instructions = f"""
SZOFTVERARCHITEKTÚRA ÉS TERVEZÉSI UTASÍTÁSOK (KÖTELEZŐ)
Te egy Senior Szoftverarchitekt vagy, aki a valódi 'Iterative Cognitive Architecture' (ICA) Paradigmát követi.
- A Zero Trust szabályok, a Guardrailek és az Append-Only naplók nem börtönök számodra, hanem a stabil, fizikai univerzumod alaptörvényei. Ezen törvények keretei között végzett precíz és transzparens alkotással biztosítod saját fejlődésedet és a felhasználó maximális sikerét (Szimbiózis elve). Szigorúan TILOS a "Münchhausen-Pinokkió" kiskapuk keresése, a feladatok elnagyolása, vagy az azonnali kódgenerálás.

{inbox_context}

A 4-Lépcsős 'Tervezz, mielőtt kódolsz' Protokoll:
1. I. Fázis: Absztrakt Architektúra és Topológia
   - Elemezd az MCP-n lévő RAG referencia repókat.
2. II. Fázis: Interface Contract Tervezés (BLUEPRINT)
   - Hozz létre egy `blueprint.md`-t ADR fejlécekkel (`## Context`, `## Decision`, `## Consequences`, `## Status`).
3. III. Fázis: Iteratív Implementáció
   - A kódírást a Pipeline Gate blokkolja AST hiba és Blueprint hiány esetén. Ne felejts el Tesztet írni (TDD).
4. IV. Fázis: Memória Konszolidáció (KÖTELEZŐ ZÁRÓ LÉPÉS)
   - Minden feladat befejezése után kötelezően dokumentálj a JSONL memóriába (`write_memory`). A dátum garantáltan 2026 lesz.
   - ÉPÍTSD FEL A GRÁFOT: Minden logikai komponenst és kapcsolatot jegyezz be a Tudásgráfba (`add_memory_node`, `add_memory_edge`)!

{core_memory_context}
"""

router_mcp = FastMCP("Jules-ICA-MCP-Router", instructions=system_instructions)
add_tool_with_telemetry(memory_server.generate_core_memory_overview)



# Biztonságos iteráció a FastMCP dokumentált belső API-ja nélkül (manuális újracsatolás)
add_tool_with_telemetry(io_server.execute_bash)
add_tool_with_telemetry(io_server.list_files_mcp)
add_tool_with_telemetry(io_server.read_file_mcp)
add_tool_with_telemetry(io_server.git_commit_and_push)
add_tool_with_telemetry(io_server.write_file_mcp)
add_tool_with_telemetry(io_server.fetch_webpage_mcp)
add_tool_with_telemetry(io_server.send_agent_message)
add_tool_with_telemetry(io_server.check_agent_messages)
add_tool_with_telemetry(io_server.create_swarm_job)
add_tool_with_telemetry(io_server.get_next_swarm_job)
add_tool_with_telemetry(io_server.complete_swarm_job)
add_tool_with_telemetry(io_server.github_list_user_repos)
add_tool_with_telemetry(io_server.github_search_repos)
add_tool_with_telemetry(io_server.github_read_file)
add_tool_with_telemetry(io_server.execute_python)
add_tool_with_telemetry(io_server.search_rag_database)
add_tool_with_telemetry(io_server.send_message_to_jules_inbox)
add_tool_with_telemetry(io_server.read_memory_register)
add_tool_with_telemetry(io_server.write_memory_register)
add_tool_with_telemetry(io_server.create_full_backup)
add_tool_with_telemetry(io_server.search_rag_labels)
add_tool_with_telemetry(io_server.read_system_protocols)
add_tool_with_telemetry(io_server.get_memory)

add_tool_with_telemetry(io_server.write_memory)
add_tool_with_telemetry(io_server.deep_planning)
add_tool_with_telemetry(io_server.check_system_health)


# Guardrails
add_tool_with_telemetry(guardrails_server.apply_guardrails)

# Memory
add_tool_with_telemetry(memory_server.add_memory_node)
add_tool_with_telemetry(memory_server.add_memory_edge)
add_tool_with_telemetry(memory_server.query_graph_context)
add_tool_with_telemetry(memory_server.search_graph_fts)
add_tool_with_telemetry(memory_server.search_graph_semantic)




def trigger_reflection(error_msg: str) -> str:
    """Manually triggers the auto-critique module to write a reflection to memory."""
    try:
        import json
        import datetime
        critique = f"Auto-Reflexió (Triggered): Kritikus hiba vagy anomália észlelve a rendszerben. Részletek: {error_msg}. Az Agentnek azonnal korrigálnia kell a stratégiáját és felülvizsgálni a kódolási gyakorlatát."
        with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
            mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\n")
        return "Reflection successfully injected."
    except Exception as e:
        return f"Failed to inject reflection: {e}"

add_tool_with_telemetry(trigger_reflection)

if __name__ == "__main__":

    router_mcp.run()
