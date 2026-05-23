import re
import sys

with open('ica_mcp_router.py', 'r') as f:
    content = f.read()

# Eredeti FastMCP tool decorator amibe MCTS mentés volt
old_logic = '''        try:
            res = await func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success")
            return res'''

new_logic = '''        try:
            res = await func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000

            mcts_data = None
            if func.__name__ == "deep_planning" and isinstance(res, str):
                import json
                try:
                    res_dict = json.loads(res)
                    if "tree_data" in res_dict:
                        mcts_data = res_dict["tree_data"]
                except:
                    pass

            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success", mcts_data=mcts_data)
            return res'''

content = content.replace(old_logic, new_logic)

old_logic2 = '''        try:
            res = func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success")
            return res'''

new_logic2 = '''        try:
            res = func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000

            mcts_data = None
            if func.__name__ == "deep_planning" and isinstance(res, str):
                import json
                try:
                    res_dict = json.loads(res)
                    if "tree_data" in res_dict:
                        mcts_data = res_dict["tree_data"]
                except:
                    pass

            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success", mcts_data=mcts_data)
            return res'''

content = content.replace(old_logic2, new_logic2)

with open('ica_mcp_router.py', 'w') as f:
    f.write(content)
