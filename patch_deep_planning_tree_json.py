import re
import sys

with open('ica_mcp_server.py', 'r') as f:
    content = f.read()

# Eredeti sor, amibe be akarunk szúrni (Már a dictionary-s verzió van ott)
old_return = '''import json
        tree_data = planner.get_tree_data()
        return {"status": "success", "best_predicted_path": best_path, "tree_data": tree_data}'''

new_return = '''import json
        tree_data = planner.get_tree_data()
        return json.dumps({"status": "success", "best_predicted_path": best_path, "tree_data": tree_data})'''

content = content.replace(old_return, new_return)

with open('ica_mcp_server.py', 'w') as f:
    f.write(content)
