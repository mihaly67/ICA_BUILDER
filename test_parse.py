import subprocess
out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>/dev/null", shell=True, text=True, timeout=1.5)
lines = out.strip().split('\n')
headers = lines[0].split()
print("Headers:", headers)
for line in lines[1:]:
    parts = line.split()
    row = dict(zip(headers[:len(parts)], parts))
    if row.get('Core') == '-' and row.get('CPU') == '-':
        print("PKG:", row.get('PkgWatt'), row.get('PkgTmp'))
    elif row.get('CPU') == '0':
        print("CPU 0:", row)
