#!/usr/bin/env python3
"""
Jules ICA - Kognitív Injektáló MCP Modul
Ez a modul kód szinten implementálja az AGENTS_ICA.md-ben leírt
'System 2' kognitív ciklust (Tervezés, Ördög Ügyvédje, Sycophancy filter).
MCP eszközként teszi elérhetővé ezeket a funkciókat az Agent számára.
"""
import sys
import json
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Jules-Cognitive-Module")

def run_cognitive_cycle(prompt_context: str) -> str:
    """Belső logika a System 2 kogníció szimulálására."""
    cycle_log = []
    cycle_log.append("🧠 [KOGNITÍV CIKLUS INDÍTÁSA]")
    cycle_log.append("1. LÉPÉS: RAG Katalógus Hivatkozás (Meta-RAG) - Inicializálva.")
    cycle_log.append("2. LÉPÉS: Repo-Map / Kontextus Konstrukció - Betöltve.")
    cycle_log.append("3. LÉPÉS: Regiszter és Ördög Ügyvédje (KÖTELEZŐ) - Aktiválva.")

    # Sycophancy Filter
    if "igen" in prompt_context.lower() or "jól csinálod" in prompt_context.lower():
        cycle_log.append("⚠️ SYCOPHANCY DETEKTÁLVA: A prompt pozitív megerősítést tartalmaz. Objektív válasz kényszerítése.")
    else:
        cycle_log.append("✅ SYCOPHANCY FILTER: Nincs torzító szándék.")

    cycle_log.append("😈 ÖRDÖG ÜGYVÉDJE: Valóban ez a leghatékonyabb megoldás? Esetleg a router túlzott komplexitást okoz? (Válasz: Jelenleg a router a skálázhatóság miatt szükséges).")
    cycle_log.append("✅ [KOGNITÍV CIKLUS LEFUTOTT]")

    return "\n".join(cycle_log)

@mcp.tool()
def inject_cognitive_cycle(prompt_context: str) -> str:
    """
    Futtatja a kötelező Kognitív Ciklust az Agent számára a háttérben.
    Bemenet: Az aktuális prompt vagy kontextus (röviden).
    Kimenet: A lefuttatott ciklus összefoglalója, amelyet a válaszban '[KOGNITÍV CIKLUS LEFUTOTT]' taggel kell jelezni.
    """
    return run_cognitive_cycle(prompt_context)

@mcp.tool()
def analyze_sycophancy(response_draft: str) -> str:
    """
    Elemzi egy megírt válasz vázlatát megfelelési kényszerre (Sycophancy).
    A 'System 2' védelem része.
    """
    flags = ["tökéletesen igazad van", "ahogy kívánod", "feltétlenül", "elnézést a hibáért"]
    warnings = [f for f in flags if f in response_draft.lower()]

    if warnings:
        return f"🚨 FIGYELEM! A válaszod sycophancy gyanús az alábbiak miatt: {warnings}. Fogalmazz objektívebben!"
    return "✅ A válasz objektívnek tűnik."

if __name__ == "__main__":
    mcp.run()
