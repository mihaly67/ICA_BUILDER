import json
import datetime
critique = "Auto-Reflexió (Fallback): Megállapítottam, hogy a FastMCP Pydantic schema errorokat teljesen elnyeli a Python szintű hibakezelés előtt (visszadobja a kliensnek anélkül, hogy a Python kódomba érne), így sem a Router wrapper, sem a Telemetria modul nem tudja rögzíteni őket. Az 'execute_bash' esetén a stderr hibaüzenet (pl. File Not Found) sem dob kivételt, csak return érték. Ezért a rendszer-szintű önkritikát és hibatűrést magasabb absztrakciós szintre (magára a kliens agentre) kell bízni, vagy az MCP hívások explicit validációjára."
with open("/home/misi/Jules_ICA_Builder/agent_memory.jsonl", "a") as mem_f:
    mem_f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "category": "Reflection", "content": critique}) + "\n")
