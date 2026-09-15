with open('local_hardware_monitor_v2_new6.py', 'r') as f:
    code = f.read()

# Fix the turbostat check processing to filter out the `[sudo] Jules jelszava: ` output so it doesn't break header parsing
search_subprocess = """            out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>/dev/null", shell=True, text=True, timeout=3.5)
            lines = out.strip().split('\\n')
            headers = []
            if lines:
                headers = lines[0].split()"""

replace_subprocess = """            out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>&1", shell=True, text=True, timeout=5)
            lines = out.strip().split('\\n')
            headers = []
            # Find the actual header line
            header_idx = -1
            for i, line in enumerate(lines):
                if 'Core' in line and 'CPU' in line and 'Avg_MHz' in line:
                    header_idx = i
                    break

            if header_idx != -1:
                # Strip sudo prompt if it prepended to the header
                header_line = lines[header_idx].split('] Jules jelszava: ')[-1]
                headers = header_line.split()
                lines = lines[header_idx+1:]"""

code = code.replace(search_subprocess, replace_subprocess)

with open('local_hardware_monitor_v2_new7.py', 'w') as f:
    f.write(code)
