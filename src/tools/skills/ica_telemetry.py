import sqlite3
import time
import os
import json

DB_PATH = "/home/misi/Jules_ICA_Builder/mcp_telemetry.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS mcp_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            tool_name TEXT,
            args TEXT,
            execution_time_ms REAL,
            status TEXT,
            error_msg TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_mcp_call(tool_name, args, execution_time_ms, status, error_msg=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO mcp_logs (timestamp, tool_name, args, execution_time_ms, status, error_msg)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (time.time(), tool_name, json.dumps(args), execution_time_ms, status, error_msg))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Telemetria hiba: {e}")

# Auto-init importkor
init_db()
