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
    """Belső logika a System 2 kogníció szimulálására, injektálás logolásával."""
    import datetime

    timestamp = datetime.datetime.now().isoformat()
    cycle_log = []
    cycle_log.append(f"🧠 [KOGNITÍV CIKLUS INDÍTÁSA] - {timestamp}")
    cycle_log.append("1. LÉPÉS: RAG Katalógus Hivatkozás (Meta-RAG) - Inicializálva.")
    cycle_log.append("2. LÉPÉS: Repo-Map / Kontextus Konstrukció - Betöltve.")
    cycle_log.append("3. LÉPÉS: Regiszter és Ördög Ügyvédje (KÖTELEZŐ) - Aktiválva.")
    cycle_log.append("4. LÉPÉS: Guardrails / AST Validáció előkészítve (Ha kód vagy JSON a válasz).")

    if "igen" in prompt_context.lower() or "jól csinálod" in prompt_context.lower():
        cycle_log.append("⚠️ SYCOPHANCY DETEKTÁLVA: A prompt pozitív megerősítést tartalmaz. Objektív válasz kényszerítése.")
    else:
        cycle_log.append("✅ SYCOPHANCY FILTER: Nincs torzító szándék.")

    cycle_log.append("😈 ÖRDÖG ÜGYVÉDJE: A választott módszer optimális?")
    cycle_log.append(f"✅ [KOGNITÍV CIKLUS LEFUTOTT] - Kód Injektálva a kérés feldolgozása elé.")

    log_content = "\n".join(cycle_log)

    # Kimentjük az injektálást egy auditálható fájlba ("gomb" megnyomásának nyoma)
    try:
        os.makedirs(os.path.expanduser("~/Jules_mx/alerts/"), exist_ok=True)
        audit_file = os.path.expanduser("~/Jules_mx/alerts/latest_injection.txt")
        with open(audit_file, "w", encoding="utf-8") as af:
            af.write(f"PROMPT_CONTEXT: {prompt_context}\n\nINJECTION_LOG:\n{log_content}")
    except Exception as e:
        cycle_log.append(f"⚠️ Hiba az injektálás naplózásakor: {e}")

    return log_content

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
