import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

old_cpu = '''        cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1\\"%\\"}'", shell=True).decode().strip()'''
old_cpu_broken = '''        cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\1/' | awk '{print 100 - $1"%"}'", shell=True).decode().strip()'''
new_cpu = '''        cpu = subprocess.check_output(r"top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\1/' | awk '{print 100 - $1\"%\"}'", shell=True).decode().strip()'''

old_disk = '''        disk = subprocess.check_output("df -h / | awk '$NF==\\"/\\"{printf \\"%s\\", $5}'", shell=True).decode().strip()'''
old_disk_broken = '''        disk = subprocess.check_output("df -h / | awk '$NF=="/"{printf "%s", $5}'", shell=True).decode().strip()'''
new_disk = '''        disk = subprocess.check_output(r"df -h / | awk '$NF==\"/\"{printf \"%s\", $5}'", shell=True).decode().strip()'''

content = content.replace(old_cpu, new_cpu)
content = content.replace(old_cpu_broken, new_cpu)
content = content.replace(old_disk, new_disk)
content = content.replace(old_disk_broken, new_disk)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
