import re

with open('vps_llama_client.py', 'r') as f:
    content = f.read()

content = content.replace("timeout=30", "timeout=120")

with open('vps_llama_client.py', 'w') as f:
    f.write(content)
