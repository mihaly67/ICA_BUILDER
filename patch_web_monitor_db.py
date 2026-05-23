import re
import sys

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# Eltávolítjuk a hibás helyen lévő conn.close()-t és betesszük a megfelelő helyre
old_logic = '''            conn.close()
            # Get latest MCTS data
            c.execute("SELECT mcts_data FROM mcp_logs WHERE tool_name='deep_planning' AND status='success' AND mcts_data IS NOT NULL ORDER BY id DESC LIMIT 1")
            mcts_row = c.fetchone()
            mcts_latest = {}
            if mcts_row and mcts_row[0]:
                try:
                    mcts_latest = json.loads(mcts_row[0])
                except:
                    pass
        except Exception as e:'''

new_logic = '''            # Get latest MCTS data
            c.execute("SELECT mcts_data FROM mcp_logs WHERE tool_name='deep_planning' AND status='success' AND mcts_data IS NOT NULL ORDER BY id DESC LIMIT 1")
            mcts_row = c.fetchone()
            mcts_latest = {}
            if mcts_row and mcts_row[0]:
                try:
                    mcts_latest = json.loads(mcts_row[0])
                except:
                    pass
            conn.close()
        except Exception as e:'''

content = content.replace(old_logic, new_logic)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
