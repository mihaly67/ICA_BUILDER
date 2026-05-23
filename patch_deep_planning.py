import re
import sys

with open('ica_mcp_server.py', 'r') as f:
    content = f.read()

# Eredeti sor, amibe be akarunk szúrni
old_return = 'import json\n        return json.dumps({"status": "success", "best_predicted_path": best_path})'

new_return = '''import json
        # Extract tree data to pass to telemetry
        tree_data = {"root_state": initial_state, "iterations": max_iterations, "best_path": best_path, "nodes": []}
        try:
            # We add a dirty hack to just dump the nodes from planner.search if possible
            # The planner doesn't return the tree natively, so we pass a simplified dict representing the outcome.
            tree_data["nodes"].append({"state": initial_state, "type": "root"})
            tree_data["nodes"].append({"state": best_path, "type": "best_child"})
        except:
            pass

        return {"status": "success", "best_predicted_path": best_path, "tree_data": tree_data}'''

content = content.replace(old_return, new_return)

with open('ica_mcp_server.py', 'w') as f:
    f.write(content)
