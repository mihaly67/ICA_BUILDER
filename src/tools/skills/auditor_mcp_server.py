#!/usr/bin/env python3
"""
Jules ICA: Auditor MCP Server (Zero Trust)
Ez a szerver biztosítja a szigorúan csak olvasható hozzáférést a Fekete Doboz naplókhoz
és a telemetria adatbázisokhoz a külső Auditor (Ellenőr) LLM-ek számára.
Szigorú Path Traversal, SQL Injection, és Data Leakage védelmekkel van ellátva.
"""

import os
import sqlite3
import re
import logging
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Konfiguráció
TARGET_DIR = "/home/misi/Jules_ICA_Builder"
PORT = 8181
AUDIT_LOG_FILE = os.path.join(TARGET_DIR, "auditor_access.log")

# Saját Audit Trail beállítása az Auditor számára
if not logging.getLogger().handlers:
    logging.basicConfig(
        filename=AUDIT_LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - AUDITOR - %(levelname)s - %(message)s'
    )

def log_audit_action(action: str, status: str, details: str):
    """Belső naplózás az auditor_access.log fájlba."""
    msg = f"Action: {action} | Status: {status} | Details: {details}"
    if status == "BLOCKED":
        logging.warning(msg)
    else:
        logging.info(msg)

# FastMCP Inicializálása
mcp = FastMCP(
    name="Jules_ICA_Auditor",
    instructions="Kizárólag a Jules ICA Fekete Doboz naplóinak és telemetriájának objektív ellenőrzésére szolgál. Nincs írási jog."
)

@mcp.tool()
def read_blackbox_log(filename: str) -> str:
    """
    Kiolvassa egy Fekete Doboz log tartalmát. Biztonsági okokból szigorúan csak a
    /home/misi/Jules_ICA_Builder/ gyökerében lévő, .log vagy .jsonl kiterjesztésű fájlokat olvashatja.
    Visszaadja a fájl utolsó 500 sorát az OOM (Memória kimerülés) elkerülése végett.
    """
    # 1. Path Traversal Védelem (Szigorú validáció)
    if ".." in filename or "/" in filename:
        log_audit_action("read_blackbox_log", "BLOCKED", f"Path Traversal kísérlet észlelve: {filename}")
        return "403 Forbidden: Path Traversal kísérlet észlelve és naplózva!"

    if not (filename.endswith(".log") or filename.endswith(".jsonl")):
        log_audit_action("read_blackbox_log", "BLOCKED", f"Jogosulatlan fájltípus: {filename}")
        return "403 Forbidden: Kizárólag .log és .jsonl fájlok olvasása engedélyezett!"

    # Biztonságos elérési út összeállítása (Szimbolikus linkek feloldása)
    safe_path = os.path.realpath(os.path.join(TARGET_DIR, filename))
    if not safe_path.startswith(os.path.realpath(TARGET_DIR)):
        log_audit_action("read_blackbox_log", "BLOCKED", f"Escaping TARGET_DIR (Symlink exploit): {safe_path}")
        return "403 Forbidden: Érvénytelen elérési út!"

    if not os.path.exists(safe_path):
        log_audit_action("read_blackbox_log", "ERROR", f"File not found: {safe_path}")
        return f"404 Not Found: A {filename} nem létezik."

    log_audit_action("read_blackbox_log", "SUCCESS", f"Accessing: {filename}")

    # 2. Fájl olvasása memóriabarát módon (OOM védelem tail-el)
    try:
        import subprocess
        # A tail -n 500 subprocess használata biztonságos, mert a safe_path már szigorúan validálva lett.
        output = subprocess.check_output(["tail", "-n", "500", safe_path]).decode('utf-8', errors='replace')
        return output
    except Exception as e:
        log_audit_action("read_blackbox_log", "ERROR", f"Read failed: {e}")
        return f"500 Internal Server Error: Hiba a fájl olvasásakor: {e}"


@mcp.tool()
def query_readonly_db(db_name: str, sql_query: str) -> str:
    """
    Kizárólag SELECT lekérdezések futtatására szolgál az objektív SQLite adatbázisokon (mcp_telemetry.db vagy ica_knowledge_graph.db).
    """
    # 1. SQL Injection / Módosítás Védelem (Regex szűrés)
    forbidden_keywords = re.compile(r'\b(DELETE|UPDATE|DROP|INSERT|ALTER|TRUNCATE|REPLACE|GRANT|REVOKE|CREATE)\b', re.IGNORECASE)
    if forbidden_keywords.search(sql_query):
        log_audit_action("query_readonly_db", "BLOCKED", f"Módosító SQL kísérlet: {sql_query}")
        return "403 Forbidden: Csak SELECT parancsok engedélyezettek az Auditor számára!"

    if not sql_query.strip().upper().startswith("SELECT"):
        log_audit_action("query_readonly_db", "BLOCKED", f"Nem SELECT SQL kísérlet: {sql_query}")
        return "403 Forbidden: A lekérdezésnek SELECT-el kell kezdődnie!"

    # 2. Adatbázis Whitelist Validáció
    allowed_dbs = ["mcp_telemetry.db", "ica_knowledge_graph.db"]
    if db_name not in allowed_dbs:
        log_audit_action("query_readonly_db", "BLOCKED", f"Ismeretlen DB: {db_name}")
        return f"403 Forbidden: Ismeretlen adatbázis. Engedélyezett: {allowed_dbs}"

    db_path = os.path.join(TARGET_DIR, db_name)
    if not os.path.exists(db_path):
        log_audit_action("query_readonly_db", "ERROR", f"DB nem található: {db_path}")
        return f"404 Not Found: A {db_name} nem létezik."

    log_audit_action("query_readonly_db", "SUCCESS", f"Querying {db_name}: {sql_query[:50]}...")

    # 3. Read-Only SQLite Kapcsolat (Fájl Descriptor szivárgás védelemmel)
    conn = None
    try:
        db_uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True, timeout=5.0)
        c = conn.cursor()
        c.execute(sql_query)
        rows = c.fetchall()

        # Oszlopnevek kinyerése a formázott JSON/szöveg kimenethez
        column_names = [description[0] for description in c.description]

        result = []
        for row in rows:
            result.append(dict(zip(column_names, row)))

        import json
        return json.dumps(result, indent=2, ensure_ascii=False)

    except sqlite3.Error as e:
        log_audit_action("query_readonly_db", "ERROR", f"SQLite hiba: {e}")
        return f"400 Bad Request: SQL Szintaktikai vagy végrehajtási hiba: {e}"
    except Exception as e:
        log_audit_action("query_readonly_db", "ERROR", f"Ismeretlen hiba: {e}")
        return f"500 Internal Server Error: {e}"
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print(f"🚀 Jules ICA Auditor MCP Server elindítva (Port {PORT})...")
    log_audit_action("SYSTEM", "START", f"Auditor MCP started on {PORT}")
    mcp.run("sse", port=PORT)
