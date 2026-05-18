#!/usr/bin/env python3
"""
Jules ICA - Kognitív Injektálás Megfigyelő (Auditor)
Ez a modul az Ollama (Llama/Qwen) használatával ellenőrzi a VPS-en,
hogy a System 2 kognitív ciklus megfelelően injektálódott-e a folyamatba.
"""
import sys
import json
import os
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Jules-Auditor-Module")

def run_local_llm(prompt: str, model: str = "qwen2.5:1.5b") -> str:
    """Meghívja a lokális Ollama-t a VPS-en."""
    try:
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        import requests
        response = requests.post("http://localhost:11434/api/generate", json=data, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "Nincs válasz az Ollamától.")
    except Exception as e:
        return f"Hiba az LLM hívásakor: {e}"

@mcp.tool()
def trigger_injection_audit() -> str:
    """
    Kiolvassa az utolsó injektálási naplót, és elküldi a Qwen-nek értékelésre.
    A Qwen megvizsgálja, hogy a kód és az injektálás helyesen történt-e.
    """
    audit_file = os.path.expanduser("~/Jules_mx/alerts/latest_injection.txt")

    if not os.path.exists(audit_file):
        return "Nincs injektálási napló (latest_injection.txt). Kérlek futtasd az inject_cognitive_cycle tool-t először!"

    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            injection_data = f.read()

        prompt = f"""Te az ICA rendszer auditora vagy. Kérlek ellenőrizd a következő Kognitív Ciklus Injektálási logot:

{injection_data}

Válaszolj a következő kérdésekre:
1. Megtörtént az injektálás?
2. Látható-e a Sycophancy filter és az Ördög Ügyvédje lépés?
3. Helyes a folyamat?

Kérlek röviden, szakmai nyelven válaszolj, mintha egy log elemzést írnál."""

        # Auditor hívás (Qwen2.5 alapértelmezetten)
        llm_evaluation = run_local_llm(prompt)

        # Mentsük el a végeredményt
        report_file = os.path.expanduser("~/Jules_mx/alerts/injection_audit_report.log")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"--- KOGNITÍV INJEKTÁLÁS AUDIT JELENTÉS ---\n{llm_evaluation}\n")

        return f"✅ Audit sikeres. Jelentés mentve a VPS-re: {report_file}\n\nQWEN AUDITOR EREDMÉNY:\n{llm_evaluation}"

    except Exception as e:
        return f"Hiba az auditálás során: {str(e)}"

if __name__ == "__main__":
    mcp.run()
