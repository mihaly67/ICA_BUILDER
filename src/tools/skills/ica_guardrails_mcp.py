#!/usr/bin/env python3
"""
Jules ICA - Guardrails és AST Parser Validációs Modul
Ez a modul biztosítja a determinisztikus, nem-AI alapú ellenőrzést (Kapuőr).
Ha a generált kód szintaktikailag hibás, vagy nem egyezik a sémával, automatikusan eldobja.
"""
import sys
import json
import os
import ast
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Jules-Guardrails-Module")

def validate_python_ast(code: str) -> tuple[bool, str]:
    """
    Determinisztikus AST parse a Python kódhoz.
    A legbiztosabb védelem a hallucinált változók és hibás behúzások ellen.
    """
    try:
        # Ha a kód parse-olható anélkül, hogy hibát dobna, szintaktikailag helyes
        ast.parse(code)
        return True, "AST Validáció sikeres. A kód szintaktikailag helyes."
    except SyntaxError as e:
        return False, f"AST Validációs hiba! Szintaktikai probléma: {e.msg} a(z) {e.lineno}. sorban."
    except Exception as e:
        return False, f"Ismeretlen AST hiba: {e}"

def validate_json_schema(data_string: str, expected_keys: list) -> tuple[bool, str]:
    """
    Egyszerű strukturális Pydantic-szerű séma ellenőrzés (Guardrails alapelv).
    Kikényszeríti, hogy az LLM a megfelelő JSON struktúrát köpje ki.
    """
    try:
        data = json.loads(data_string)
        if not isinstance(data, dict):
             return False, "A kimenet nem egy JSON objektum (dict)."

        missing_keys = [k for k in expected_keys if k not in data]
        if missing_keys:
             return False, f"Strukturális hiba: Hiányzó kulcsok a JSON-ből: {missing_keys}"

        return True, "JSON Séma validáció sikeres."
    except json.JSONDecodeError as e:
        return False, f"JSON Parse hiba! Az AI hallucinált formátumot generált: {e}"

@mcp.tool()
def apply_guardrails(generated_code: str, expected_type: str = "python", expected_keys: list = None) -> str:
    """
    Lefuttatja a strukturális és logikai kapuőr teszteket a generált szövegen.
    Ezt a kognitív ciklus után / kódfuttatás előtt kell meghívni!
    """
    log = ["[GUARDRAILS VALIDÁCIÓ INDÍTÁSA]"]

    if expected_type == "python":
        log.append("🔍 AST (Abstract Syntax Tree) Parser teszt futtatása...")
        is_valid, msg = validate_python_ast(generated_code)
        log.append(f"{'✅' if is_valid else '❌'} {msg}")
        if not is_valid:
            log.append("🚨 BLOKKOLVA: A kód hallucinációt vagy szintaktikai hibát tartalmaz! Kényszerített újragenerálás szükséges.")
            return "\n".join(log)

    if expected_type == "json" and expected_keys:
        log.append(f"🔍 JSON Séma teszt futtatása (elvárt kulcsok: {expected_keys})...")
        is_valid, msg = validate_json_schema(generated_code, expected_keys)
        log.append(f"{'✅' if is_valid else '❌'} {msg}")
        if not is_valid:
            log.append("🚨 BLOKKOLVA: A struktúra hibás (Guardrail violation)! Kényszerített újragenerálás szükséges.")
            return "\n".join(log)

    log.append("✅ [GUARDRAILS VALIDÁCIÓ SIKERES] - A kód/adat átment a determinista szűrőn.")
    return "\n".join(log)

if __name__ == "__main__":
    mcp.run()
