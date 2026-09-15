import os
import psutil

def get_cpu_cstates(cpu_count):
    cstate_info = {}
    for i in range(cpu_count):
        base_path = f"/sys/devices/system/cpu/cpu{i}/cpuidle"
        if not os.path.exists(base_path):
            continue

        # We need to find the state with the highest time or check which one is active
        # The 'time' file contains the total time spent in that C-state in microseconds
        best_state_name = "C0" # Default active
        # This is cumulative time, so determining instantaneous C-state is tricky.
        # Alternatively, we just display the available states for now, or use a delta.
        cstate_info[i] = "C0"
    return cstate_info

print(get_cpu_cstates(psutil.cpu_count()))
