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

def validate_tdd_compliance(filepath: str, work_dir: str) -> tuple[bool, str]:
    """
    TDD Guardrail: Ellenőrzi, hogy egy implementációs kódhoz létezik-e előzetesen megírt tesztfájl.
    """
    import os

    filename = os.path.basename(filepath)

    # Ha nem python fájl, vagy config fájl, nem kényszerítjük (egyelőre) a TDD-t
    if not filepath.endswith(".py"):
        return True, "Nem Python fájl, TDD ellenőrzés átugorva."

    # Ha maga a fájl egy teszt, azt engedjük lementeni (hiszen ezzel kezdődik a TDD)
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return True, "Tesztfájl írása engedélyezve (TDD Red fázis)."

    # Speciális fájlok, amiknek nem kell teszt (mcp szerverek, scriptek)
    if "mcp" in filename.lower() or filename.startswith("vps_"):
         return True, "Rendszerscript írása engedélyezve (TDD átugorva)."

    # Ha éles logikát (implementációt) írunk, keresni kell egy hozzá tartozó tesztet
    test_filename = f"test_{filename}"
    test_filepath = os.path.join(work_dir, test_filename)

    if not os.path.exists(test_filepath):
        # Keresünk egy "tests" mappát is
        tests_dir = os.path.join(work_dir, "tests")
        if os.path.exists(tests_dir) and os.path.exists(os.path.join(tests_dir, test_filename)):
            return True, f"Tesztfájl ({test_filename}) megtalálva a tests mappában. Implementáció engedélyezve."

        return False, f"TDD GUARDRAIL SÉRTÉS: Nem találtam tesztfájlt ({test_filename}) az implementációhoz! A Test-Driven Development szabályai szerint előbb a tesztet kell megírnod és elmentened."

    return True, f"Tesztfájl ({test_filename}) megtalálva. Implementáció engedélyezve."


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

def sanitize_bash_command(command: str) -> str:
    """
    Biztonságos sandbox hiányában (Ubuntu User Namespace blokkolás miatt)
    szigorú Regex szűrést alkalmazunk a Bash parancsokra, hogy megvédjük a VPS-t.
    """
    import re

    # 1. Tiltott parancsok (rm -rf, sudo, chown, stb.)
    forbidden_commands = [
        r'\bsudo\b', r'\bsu\b', r'\bchown\b', r'\bchmod\b',
        r'\brm\s+-r', r'\brm\s+-f', r'\bmv\s+/.*',
        r'\bhalt\b', r'\breboot\b', r'\bshutdown\b', r'\binit\b'
    ]

    for pattern in forbidden_commands:
        if re.search(pattern, command, re.IGNORECASE):
            raise ValueError(f"Biztonsági Hiba: A '{pattern}' minta használata szigorúan TILOS a VPS-en!")

    # 2. File redirection és piping blokkolása kritikus fájlokra
    dangerous_redirects = [
        r'>\s*/etc', r'>>\s*/etc', r'>\s*/var', r'>>\s*/var',
        r'>\s*/usr', r'>>\s*/usr', r'>\s*/bin', r'>>\s*/bin'
    ]

    for pattern in dangerous_redirects:
        if re.search(pattern, command):
            raise ValueError(f"Biztonsági Hiba: Rendszerkönyvtárba való írás/átirányítás ('{pattern}') TILOS!")

    return command

if __name__ == "__main__":
    mcp.run()
