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
            error_msg TEXT,
            mcts_data TEXT
        )
    """)
    # Try adding the column if it doesn't exist (SQLite doesn't have IF NOT EXISTS for columns)
    try:
        c.execute("ALTER TABLE mcp_logs ADD COLUMN mcts_data TEXT;")
    except sqlite3.OperationalError:
        pass # Column already exists
    conn.commit()
    conn.close()

def log_mcp_call(tool_name, args, execution_time_ms, status, error_msg="", mcts_data=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO mcp_logs (timestamp, tool_name, args, execution_time_ms, status, error_msg, mcts_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (time.time(), tool_name, json.dumps(args), execution_time_ms, status, error_msg, json.dumps(mcts_data) if mcts_data else None))
        conn.commit()
        conn.close()
    except Exception as e:
        import sys
        print(f"Telemetria hiba: {e}", file=sys.stderr)

# Auto-init importkor
init_db()
