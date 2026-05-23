import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# Keresünk a hibás sorra, és kijavítjuk az idézőjelek escape-elését
old_line = '''        mem = subprocess.check_output("free -m | awk 'NR==2{printf \\"%.2f%%\\", $3*100/$2 }'", shell=True).decode().strip()'''
# Ha a python valahogy eltüntette a backslasheket a korábbi patchnél, próbáljuk megkeresni az escape nélküli verziót is:
old_line_broken = '''        mem = subprocess.check_output("free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }'", shell=True).decode().strip()'''

# Helyes string formázás: használjunk szimpla idézőjeleket kívül, dupla idézőjelet a bashhez, és azon belül a formátumot
new_line = '''        mem = subprocess.check_output('free -m | awk \\'NR==2{printf "%.2f%%", $3*100/$2 }\\'', shell=True).decode().strip()'''

content = content.replace(old_line, new_line)
content = content.replace(old_line_broken, new_line)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
