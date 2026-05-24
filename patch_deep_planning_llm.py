import re

with open('ica_mcp_server.py', 'r') as f:
    content = f.read()

# We need to replace qwen2.5:1.5b with something smaller/faster if it's struggling,
# or we just rely on keep_alive parameter. Since we added keep_alive, let's just make sure
# deep_planning is calling it efficiently and limit iterations more explicitly if needed.
# Actually, the user analysis stated that despite the slowness, error rate is low.
# Let's fix the System 2 Planner logic to not overwhelm the LLM.
old_gen = '''        def gen_func(state):
            prompt = f"Adott az alábbi állapot/kérdés: '{state}'. Sorolj fel maximum 3 logikus következő lépést vagy alcélt, amit meg kellene tenni a megoldásához. Csak a lépéseket írd le egymás alá, pontozás nélkül."'''

new_gen = '''        def gen_func(state):
            prompt = f"Állapot: '{state}'. Sorolj fel max 2 logikus következő lépést a megoldáshoz. Tömören, egymás alá."'''

content = content.replace(old_gen, new_gen)

with open('ica_mcp_server.py', 'w') as f:
    f.write(content)
