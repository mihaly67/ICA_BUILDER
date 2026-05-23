import re

with open('ica_mcp_server.py', 'r') as f:
    content = f.read()

content = content.replace("timeout=15", "timeout=120")

with open('ica_mcp_server.py', 'w') as f:
    f.write(content)
