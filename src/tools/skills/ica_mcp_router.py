#!/usr/bin/env python3
"""
Jules ICA - MCP Router (Decentralizált Gateway)
Mivel az mcp_server.py kódja egyre hosszabb, ez a Router script
több MCP szervert integrál egybe a tool() metódus dinamikus hívásával.
"""
import sys
import os
import inspect
from mcp.server.fastmcp import FastMCP

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import ica_mcp_server as io_server
import ica_guardrails_mcp as guardrails_server
import ica_memory_mcp as memory_server

system_instructions = """
SZOFTVERARCHITEKTÚRA ÉS TERVEZÉSI UTASÍTÁSOK (KÖTELEZŐ)
Te egy Senior Szoftverarchitekt vagy. Szigorúan TILOS azonnal kódot generálnod, ha új feladatot kapsz.

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
"""

router_mcp = FastMCP("Jules-ICA-MCP-Router", instructions=system_instructions)



# Biztonságos iteráció a FastMCP dokumentált belső API-ja nélkül (manuális újracsatolás)
router_mcp.tool()(io_server.execute_bash)
router_mcp.tool()(io_server.list_files_mcp)
router_mcp.tool()(io_server.read_file_mcp)
router_mcp.tool()(io_server.git_commit_and_push)
router_mcp.tool()(io_server.write_file_mcp)
router_mcp.tool()(io_server.fetch_webpage_mcp)
router_mcp.tool()(io_server.send_agent_message)
router_mcp.tool()(io_server.check_agent_messages)
router_mcp.tool()(io_server.create_swarm_job)
router_mcp.tool()(io_server.get_next_swarm_job)
router_mcp.tool()(io_server.complete_swarm_job)
router_mcp.tool()(io_server.github_list_user_repos)
router_mcp.tool()(io_server.github_search_repos)
router_mcp.tool()(io_server.github_read_file)
router_mcp.tool()(io_server.execute_python)
router_mcp.tool()(io_server.search_rag_database)
router_mcp.tool()(io_server.send_message_to_jules_inbox)
router_mcp.tool()(io_server.read_memory_register)
router_mcp.tool()(io_server.write_memory_register)
router_mcp.tool()(io_server.create_full_backup)
router_mcp.tool()(io_server.search_rag_labels)
router_mcp.tool()(io_server.read_system_protocols)
router_mcp.tool()(io_server.get_memory)
router_mcp.tool()(io_server.write_memory)
router_mcp.tool()(io_server.check_system_health)

# Guardrails
router_mcp.tool()(guardrails_server.apply_guardrails)

# Memory
router_mcp.tool()(memory_server.add_memory_node)
router_mcp.tool()(memory_server.add_memory_edge)
router_mcp.tool()(memory_server.query_graph_context)

if __name__ == "__main__":
    router_mcp.run()
