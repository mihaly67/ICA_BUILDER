import subprocess
import re

def get_cstates_cpupower():
    try:
        # Futtatjuk a cpupower monitort ami azonnal visszatér
        out = subprocess.check_output("cpupower monitor", shell=True, text=True, stderr=subprocess.DEVNULL)
        lines = out.strip().split('\n')
        # Megkeressük a fejlécet, pl:  CPU| || POLL | C1   | C1E  | C3   | C6
        headers = []
        data = {}
        for line in lines:
            if line.strip().startswith("CPU|"):
                headers = [h.strip() for h in line.replace("||", "|").split("|") if h.strip()]
            elif re.match(r'^\s*\d+\|', line):
                parts = [p.strip() for p in line.replace("||", "|").split("|") if p.strip()]
                if len(parts) >= len(headers):
                    cpu_idx = int(parts[0])
                    states = {}
                    for i in range(1, len(headers)):
                        try:
                            val = float(parts[i].replace(',', '.'))
                            states[headers[i]] = val
                        except:
                            pass
                    data[cpu_idx] = states
        return data
    except Exception as e:
        print(e)
        return {}

print(get_cstates_cpupower())
