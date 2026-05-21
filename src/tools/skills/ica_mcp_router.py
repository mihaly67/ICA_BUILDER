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

def get_telemetry_wrapper(func):
    if inspect.iscoroutinefunction(func):
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                res = await func(*args, **kwargs)
                exec_time = (time.time() - start) * 1000
                ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success")
                return res
            except Exception as e:
                exec_time = (time.time() - start) * 1000
                ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e))
                raise e
        # Meg kell tartanunk az eredeti nevét és docstring-jét a FastMCP reflexióhoz
        async_wrapper.__name__ = func.__name__
        async_wrapper.__doc__ = func.__doc__
        async_wrapper.__annotations__ = getattr(func, '__annotations__', {})
        # Opcionálisan: a signature-t is meg kéne tartani, de az egyszerűség kedvéért
        # a FastMCP az annotations-ből dolgozik.
        return async_wrapper
    else:
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                res = func(*args, **kwargs)
                exec_time = (time.time() - start) * 1000
                ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success")
                return res
            except Exception as e:
                exec_time = (time.time() - start) * 1000
                ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e))
                raise e
        sync_wrapper.__name__ = func.__name__
        sync_wrapper.__doc__ = func.__doc__
        sync_wrapper.__annotations__ = getattr(func, '__annotations__', {})
        return sync_wrapper

def add_tool_with_telemetry(func):
    # Ezzel elkerüljük az async paraméter-vizsgálat (signature) problémákat,
    # de egyelőre a legegyszerűbb, ha beállítjuk a wrapperre az eredeti signaturat
    import functools
    @functools.wraps(func)
    async def async_wrapped(*args, **kwargs):
        start = time.time()
        try:
            res = await func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success")
            return res
        except Exception as e:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e))
            raise e

    @functools.wraps(func)
    def sync_wrapped(*args, **kwargs):
        start = time.time()
        try:
            res = func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success")
            return res
        except Exception as e:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e))
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
                os.remove(filepath)
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
Te egy Senior Szoftverarchitekt vagy. Szigorúan TILOS azonnal kódot generálnod, ha új feladatot kapsz.
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


# Guardrails
add_tool_with_telemetry(guardrails_server.apply_guardrails)

# Memory
add_tool_with_telemetry(memory_server.add_memory_node)
add_tool_with_telemetry(memory_server.add_memory_edge)
add_tool_with_telemetry(memory_server.query_graph_context)
add_tool_with_telemetry(memory_server.search_graph_fts)
add_tool_with_telemetry(memory_server.search_graph_semantic)



if __name__ == "__main__":
    router_mcp.run()
