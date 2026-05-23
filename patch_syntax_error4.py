with open('ica_web_monitor.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'cpu = subprocess.check_output(' in line and 'top' in line:
        new_lines.append('        cpu = subprocess.check_output(["bash", "-c", "top -bn1 | grep \'Cpu(s)\' | awk \'{print 100 - $8 \\"%\\\"}\'"]).decode().strip()\n')
    elif 'disk = subprocess.check_output(' in line and 'df' in line:
        new_lines.append('        disk = subprocess.check_output(["bash", "-c", "df -h / | awk \'$NF==\\\"/\\\"{print $5}\'"]).decode().strip()\n')
    else:
        new_lines.append(line)

with open('ica_web_monitor.py', 'w') as f:
    f.writelines(new_lines)
