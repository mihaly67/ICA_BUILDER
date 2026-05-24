import sys
import subprocess
import time

def main():
    cmds = [
        ["python3", "tools/skills/mcp_bridge_tool.py", "--tool", "check_system_health", "--args", "{}"],
        ["python3", "tools/skills/mcp_bridge_tool.py", "--tool", "get_next_swarm_job", "--args", '{"agent_id": "Raj_Monitor"}'],
        ["python3", "tools/skills/mcp_bridge_tool.py", "--tool", "search_rag_labels", "--args", '{"target_dir": "/home/misi/MQL5_Theory/"}']
    ]
    for cmd in cmds:
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, env={"VPS_PWD": "1104", "VPS_HOST": "5.189.163.88", **os.environ})
        time.sleep(2)

if __name__ == "__main__":
    import os
    main()
