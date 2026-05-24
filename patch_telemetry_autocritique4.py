import re

with open('ica_telemetry.py', 'r') as f:
    content = f.read()

# Eltávolítom az összes eddigi próbálkozást és beteszek egy hibabiztosat
old_func = '''def log_mcp_call(tool_name, args, execution_time_ms, status, error_msg="", mcts_data=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO mcp_logs (timestamp, tool_name, args, execution_time_ms, status, error_msg, mcts_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (time.time(), tool_name, json.dumps(args), execution_time_ms, status, error_msg, json.dumps(mcts_data) if mcts_data else None))
        conn.commit()
        conn.close()

        # AGGRESSIVE AUTO CRITIQUE TRIGGER
        if status == "error" or (error_msg and len(str(error_msg)) > 0):
            try:
                import datetime
                err_msg_clean = str(error_msg).replace('"', "'")
                critique = f"Auto-Reflexió (Telemetry): A '{tool_name}' eszköz hibára futott. Ok: {err_msg_clean}. Felülvizsgálat szükséges."
                with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
                    mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\\n")
            except Exception as trig_e:
                print(f"Trigger error: {trig_e}")

    except Exception as e:
        import sys
        print(f"Telemetria hiba: {e}", file=sys.stderr)'''

new_func = '''def log_mcp_call(tool_name, args, execution_time_ms, status, error_msg="", mcts_data=None):
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

    # AUTO CRITIQUE TRIGGER MINDIG, ha a status error VAGY az error_msg nem ures
    if status == "error" or (error_msg and len(str(error_msg)) > 0):
        try:
            import datetime
            err_msg_clean = str(error_msg).replace('"', "'")
            critique = f"Ördög Ügyvédje (Auto): A '{tool_name}' eszköz hibára futott. Ok: {err_msg_clean}. Felülvizsgálat szükséges."
            with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
                mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\\n")
        except Exception as trig_e:
            import sys
            print(f"Trigger error: {trig_e}", file=sys.stderr)'''

content = content.replace(old_func, new_func)

with open('ica_telemetry.py', 'w') as f:
    f.write(content)
