with open('local_hardware_monitor_v2_new5.py', 'r') as f:
    code = f.read()

# Increase timeout and fix turbostat check output format handling
search_subprocess = """            out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>/dev/null", shell=True, text=True, timeout=1.5)"""

replace_subprocess = """            out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>/dev/null", shell=True, text=True, timeout=3.5)"""

code = code.replace(search_subprocess, replace_subprocess)

with open('local_hardware_monitor_v2_new6.py', 'w') as f:
    f.write(code)
