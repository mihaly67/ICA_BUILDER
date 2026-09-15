import time
import os

def read_cstates(cpu_idx):
    base = f"/sys/devices/system/cpu/cpu{cpu_idx}/cpuidle"
    states = {}
    if not os.path.exists(base): return states
    try:
        for state_dir in os.listdir(base):
            if state_dir.startswith("state"):
                name = open(os.path.join(base, state_dir, "name")).read().strip()
                t = int(open(os.path.join(base, state_dir, "time")).read().strip())
                states[name] = t
    except Exception:
        pass
    return states

t1 = read_cstates(0)
time.sleep(1)
t2 = read_cstates(0)

print(t1)
print(t2)
deltas = {k: t2[k] - t1.get(k, 0) for k in t2}
print(deltas)
