#!/usr/bin/env python3
"""
Jules ICA - MCP Router (Decentralizált Gateway)
Mivel az mcp_server.py kódja egyre hosszabb, ez a Router script
több MCP szervert (Pl. IO Server és Cognitive Server) integrál egybe,
lehetővé téve a skálázható architektúrát a stdio csatornán.
"""
import sys
import os
from mcp.server.fastmcp import FastMCP

# Modulok betöltése
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import ica_mcp_server as io_server
import ica_cognitive_mcp as cognitive_server
import ica_auditor_mcp as auditor_server
import ica_guardrails_mcp as guardrails_server

router_mcp = FastMCP("Jules-ICA-MCP-Router")

# Eszközök dinamikus regisztrálása a list_tools alapján
for server in [io_server, cognitive_server, auditor_server, guardrails_server]:
    for tool_obj in server.mcp._tool_manager.list_tools():
        router_mcp.tool(name=tool_obj.name, description=tool_obj.description)(tool_obj.fn)

if __name__ == "__main__":
    router_mcp.run()
