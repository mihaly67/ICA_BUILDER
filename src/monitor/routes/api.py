from flask import Blueprint, jsonify
from src.monitor.utils.db import get_db_connection, DB_PATH, GRAPH_DB_PATH
from src.monitor.utils.system import get_system_health, get_swarm_inbox
from src.monitor.utils.memory import get_memory_stats_and_entries, get_blueprint_status
import sqlite3
import json
import os
import uuid
import logging
import html
import time

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/data')
def get_data():
    # 1. Telemetria Lekérése (SQLite)
    stats = {"total": 0, "avg_time": 0, "error_rate": 0}
    telemetry_rows = []
    mcts_latest = {}
    guardrails_html = ""

    if os.path.exists(DB_PATH):
        conn = get_db_connection(DB_PATH, read_only=True)
        try:
            if conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*), AVG(execution_time_ms) FROM mcp_logs")
                row = c.fetchone()
                total = row[0] if row[0] else 0
                avg_time = round(row[1], 1) if row[1] else 0

                c.execute("SELECT COUNT(*) FROM mcp_logs WHERE status='error'")
                errors_row = c.fetchone()
                errors = errors_row[0] if errors_row else 0

                if total:
                    stats = {
                        "total": total,
                        "avg_time": avg_time,
                        "error_rate": round((errors / total * 100), 1) if total > 0 else 0
                    }

                c.execute("SELECT timestamp, tool_name, args, execution_time_ms, status, error_msg FROM mcp_logs ORDER BY id DESC LIMIT 20")
                for r in c.fetchall():
                    ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r[0]))
                    telemetry_rows.append({
                        "time": ts_str,
                        "tool_name": r[1],
                        "args_raw": r[2],
                        "duration": r[3],
                        "status": r[4],
                        "error": html.escape(str(r[5])) if r[5] else ""
                    })

                c.execute("SELECT mcts_data FROM mcp_logs WHERE tool_name='deep_planning' AND status='success' AND mcts_data IS NOT NULL ORDER BY id DESC LIMIT 1")
                mcts_row = c.fetchone()
                if mcts_row and mcts_row[0]:
                    try:
                        mcts_latest = json.loads(mcts_row[0])
                    except Exception as ex:
                        mcts_latest = {"name": f"Hiba a JSON parszolásban: {ex}"}

                c.execute("SELECT COUNT(*), SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) FROM mcp_logs WHERE tool_name='write_file_mcp'")
                gr_row = c.fetchone()
                if gr_row:
                    write_total, write_errs = gr_row
                    write_errs = write_errs if write_errs else 0
                    write_total = write_total if write_total else 0
                    success_rate = ((write_total - write_errs) / write_total * 100) if write_total > 0 else 100
                    color = "text-success" if success_rate > 90 else ("text-warning" if success_rate > 70 else "text-danger")
                    guardrails_html = f"<div>ADR & AST Validációs Arány: <b class='{color}'>{success_rate:.1f}%</b></div>"
                    guardrails_html += f"<div>Összes fájl írási kísérlet: <b>{write_total}</b></div>"
                    guardrails_html += f"<div>Blokkolt / Hiba: <b class='text-danger'>{write_errs}</b></div>"

        except sqlite3.Error as e:
            mcts_latest = {"name": f"Adatbázis hiba: {e}"}
            guardrails_html = f"Adatbázis hiba: {e}"
        except Exception as e:
            mcts_latest = {"name": f"Ismeretlen hiba: {e}"}
        finally:
            if conn:
                conn.close()

    memory_entries, memory_stats, reflection_html = get_memory_stats_and_entries()
    blueprint_html = get_blueprint_status()
    system_health_str = get_system_health()
    inbox_str = get_swarm_inbox()

    graph_nodes = []
    graph_edges = []
    if os.path.exists(GRAPH_DB_PATH):
        conn_g = get_db_connection(GRAPH_DB_PATH, read_only=True)
        try:
            if conn_g:
                cg = conn_g.cursor()
                cg.execute("SELECT id, name, type, description FROM entities")
                for r in cg.fetchall():
                    graph_nodes.append({"id": r[0], "name": r[1], "type": r[2], "description": r[3]})

                cg.execute("SELECT source_id, target_id, relationship FROM edges")
                for r in cg.fetchall():
                    graph_edges.append({"source_id": r[0], "target_id": r[1], "relationship": r[2]})
        except Exception as e:
            err_id = str(uuid.uuid4())[:8]
            logging.error(f"Error [{err_id}] in Graph DB: {e}", exc_info=True)
        finally:
            if conn_g:
                conn_g.close()

    return jsonify({
        "stats": stats,
        "telemetry": telemetry_rows,
        "memory": memory_entries,
        "guardrails_html": guardrails_html,
        "blueprint_html": blueprint_html,
        "reflection_html": reflection_html,
        "system_health": system_health_str,
        "swarm_inbox": inbox_str,
        "mcts_latest": mcts_latest,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "memory_stats": memory_stats
    })
