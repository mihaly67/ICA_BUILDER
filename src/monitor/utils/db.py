import sqlite3
import os
import json
import logging
import html
import uuid

DB_PATH = "/home/misi/Jules_ICA_Builder/mcp_telemetry.db"
GRAPH_DB_PATH = "/home/misi/Jules_ICA_Builder/ica_knowledge_graph.db"

def get_db_connection(db_path, read_only=True):
    try:
        if read_only:
            uri = f"file:{db_path}?mode=ro"
            return sqlite3.connect(uri, uri=True, timeout=5.0)
        else:
            return sqlite3.connect(db_path, timeout=5.0)
    except Exception as e:
        err_id = str(uuid.uuid4())[:8]
        logging.error(f"Error [{err_id}] connecting to DB {db_path}: {e}", exc_info=True)
        return None
