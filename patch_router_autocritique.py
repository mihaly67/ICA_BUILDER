import re

with open('ica_mcp_router.py', 'r') as f:
    content = f.read()

old_error_logic = '''        except Exception as e:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e), mcts_data=mcts_data)
            raise e'''

new_error_logic = '''        except Exception as e:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e), mcts_data=mcts_data)

            # AUTO-CRITIQUE TRIGGER
            try:
                import json
                import datetime
                err_msg = str(e).replace('"', "'")
                critique = f"Auto-Reflexió: A '{func.__name__}' eszköz hibára futott. Ok: {err_msg}. Az Agentnek felül kell vizsgálnia a stratégiát, mert valószínűleg megsértett egy Guardrailt vagy hibás argumentumokat adott át."
                with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
                    mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\\n")
            except:
                pass

            raise e'''

content = content.replace(old_error_logic, new_error_logic)

with open('ica_mcp_router.py', 'w') as f:
    f.write(content)
