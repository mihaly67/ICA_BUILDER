import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# A hiba az volt, hogy 'c_new.execute' után 'c.fetchone()'-t hívtunk a zárt c kurzoron.
old_logic = '''        c_new.execute("SELECT COUNT(*), SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) FROM mcp_logs WHERE tool_name='write_file_mcp'")
        write_total, write_errs = c.fetchone()'''

new_logic = '''        c_new.execute("SELECT COUNT(*), SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) FROM mcp_logs WHERE tool_name='write_file_mcp'")
        write_total, write_errs = c_new.fetchone()'''

content = content.replace(old_logic, new_logic)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
