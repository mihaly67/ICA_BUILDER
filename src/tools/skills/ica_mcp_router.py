#!/usr/bin/env python3
"""
Jules ICA - MCP Router (Decentralizált Gateway)
"""
import sys
import os
from mcp.server.fastmcp import FastMCP

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import ica_mcp_server as io_server
import ica_guardrails_mcp as guardrails_server

system_instructions = """
SZOFTVERARCHITEKTÚRA ÉS TERVEZÉSI UTASÍTÁSOK (KÖTELEZŐ)
Te egy Senior Szoftverarchitekt vagy. Szigorúan TILOS azonnal kódot generálnod, ha új feladatot kapsz.

A 3-Lépcsős 'Tervezz, mielőtt kódolsz' Protokoll:
1. I. Fázis: Absztrakt Architektúra és Topológia (GONDOLKODÁSI FÁZIS)
   - Elemezd az MCP-n lévő RAG referencia repókat (pl. `joelparkerhenderson/architecture-decision-record`). Keresd meg a közös építészeti mintákat.
2. II. Fázis: Interface Contract Tervezés (BLUEPRINT FÁZIS)
   - Hozz létre egy `blueprint.md` dokumentumot, amely rögzíti a felépítést. Ezt a `write_file_mcp` eszközzel kell mentened.
   - A `blueprint.md`-nek TARTALMAZNIA KELL a hivatalos ADR fejléceket: `## Context`, `## Decision`, `## Consequences`, `## Status`. Ha ezek hiányoznak, az MCP szerver visszadobja a fájlt.
3. III. Fázis: Iteratív Implementáció (VERIFIKÁCIÓS FÁZIS)
   - A kódírást a `write_file_mcp` blokkolja, ha a `blueprint.md` nincs kész, vagy ha a Python kód szintaktikailag hibás (AST Guardrail).
   - A JSON/adat kimeneteket GBNF / Pydantic minták alapján formázd.

[ÖRDÖG ÜGYVÉDJE KÉRDÉS MAGADHOZ]: Valóban készen van a tervem mielőtt kódot írok? Nem fog szintaktikai hibát dobni az AST parser?
"""

router_mcp = FastMCP("Jules-ICA-MCP-Router", instructions=system_instructions)

for server in [io_server, guardrails_server]:
    for tool_obj in server.mcp._tool_manager.list_tools():
        router_mcp.tool(name=tool_obj.name, description=tool_obj.description)(tool_obj.fn)

if __name__ == "__main__":
    router_mcp.run()
