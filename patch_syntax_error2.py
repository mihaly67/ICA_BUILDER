import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

old_ref = '''                reflection_html = f"<span class='text-secondary'>[{ts}]</span> <b class='text-danger'>[{cat}]</b><br><i style='color: #e2e8f0;'>"{content}"</i>"'''
new_ref = '''                reflection_html = f"<span class='text-secondary'>[{ts}]</span> <b class='text-danger'>[{cat}]</b><br><i style='color: #e2e8f0;'>\\\"{content}\\\"</i>"'''

content = content.replace(old_ref, new_ref)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
