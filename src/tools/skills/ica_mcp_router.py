#!/usr/bin/env python3
"""
Jules ICA - MCP Router (Decentralizált Gateway)
Mivel az mcp_server.py kódja egyre hosszabb, ez a Router script
több MCP szervert (Pl. IO Server és Cognitive Server) integrál egybe,
lehetővé téve a skálázható architektúrát a stdio csatornán.
(Jelenleg egy szimpla FastMCP proxyként viselkedik, amely importálja a többi eszközt.)
"""
import sys
import os
from mcp.server.fastmcp import FastMCP

# Modulok importálása a lokális könyvtárból
# (VPS-en a ~/Jules_ICA_Builder/ könyvtárban lesznek)
try:
    import ica_mcp_server as io_server
    import ica_cognitive_mcp as cognitive_server
except ImportError:
    # Biztosítás, ha a futtatás más mappából történik
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import ica_mcp_server as io_server
    import ica_cognitive_mcp as cognitive_server

# Létrehozunk egy központi router FastMCP példányt
router_mcp = FastMCP("Jules-ICA-MCP-Router")

# Átemeljük a regisztrált eszközöket a másik két szerverről
for name, tool_func in io_server.mcp._tool_manager._tools.items():
    router_mcp.tool(name=name, description=tool_func.description)(tool_func.fn)

for name, tool_func in cognitive_server.mcp._tool_manager._tools.items():
    router_mcp.tool(name=name, description=tool_func.description)(tool_func.fn)

if __name__ == "__main__":
    router_mcp.run()
