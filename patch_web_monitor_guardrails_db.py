import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

old_guardrails = '''    # Kognitív Pipeline Adatok (Guardrails, Blueprint, Önreflexió)
    guardrails_html = ""
    try:
        # Guardrails telemetria olvasása
        c.execute("SELECT COUNT(*), SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) FROM mcp_logs WHERE tool_name='write_file_mcp'")'''

new_guardrails = '''    # Kognitív Pipeline Adatok (Guardrails, Blueprint, Önreflexió)
    guardrails_html = ""
    try:
        conn = sqlite3.connect(DB_PATH)
        c_new = conn.cursor()
        # Guardrails telemetria olvasása
        c_new.execute("SELECT COUNT(*), SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) FROM mcp_logs WHERE tool_name='write_file_mcp'")'''

content = content.replace(old_guardrails, new_guardrails)

old_guardrails_end = '''        guardrails_html += f"<div>Blokkolt / Hiba: <b class='text-danger'>{write_errs}</b></div>"
    except Exception as e:'''

new_guardrails_end = '''        guardrails_html += f"<div>Blokkolt / Hiba: <b class='text-danger'>{write_errs}</b></div>"
        conn.close()
    except Exception as e:'''

content = content.replace(old_guardrails_end, new_guardrails_end)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
