import re

with open('local_hardware_monitor_v2_new4.py', 'r') as f:
    code = f.read()

# I notice that `turbostat` output does not correctly parse if it requires the password to execute without hanging,
# but the current execution `subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>/dev/null", ...)`
# actually works because it was tested and gave full output!
# I will make sure the text coloring logic and the temperature parsing is robust.

search_update = """        # 1.1 Frequencies, Temps, C-States via turbostat
        freqs = {}
        core_temps = {}
        cstates = {}
        pkg_watt = "N/A"
        pkg_temp = "N/A"

        try:
            # We use sudo -S with a placeholder or pkexec. The user environment allows sudo without TTY if properly configured.
            # To avoid hanging the UI thread, we run a non-blocking check or a quick timeout.
            out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>/dev/null", shell=True, text=True, timeout=1.5)
            lines = out.strip().split('\\n')
            headers = []
            if lines:
                headers = lines[0].split()

            for line in lines[1:]:
                parts = line.split()
                if not parts:
                    continue

                row = dict(zip(headers, parts))

                # Overall Package info (Core and CPU column usually '-')
                if row.get('Core') == '-' and row.get('CPU') == '-':
                    if 'PkgWatt' in row: pkg_watt = row['PkgWatt']
                    if 'PkgTmp' in row: pkg_temp = f"{row['PkgTmp']}°C"
                    continue

                try:
                    cpu_idx = int(row.get('CPU', -1))
                    if cpu_idx >= 0:
                        if 'Avg_MHz' in row: freqs[cpu_idx] = float(row['Avg_MHz'])
                        if 'CoreTmp' in row: core_temps[cpu_idx] = float(row['CoreTmp'])

                        states = {}
                        for st in ['C1%', 'C1E%', 'C3%', 'C6%', 'POLL%']:
                            if st in row:
                                try: states[st.replace('%', '')] = float(row[st])
                                except: pass
                        cstates[cpu_idx] = states
                except:
                    pass
        except Exception as e:
            pass"""

replace_update = """        # 1.1 Frequencies, Temps, C-States via turbostat
        freqs = {}
        core_temps = {}
        cstates = {}
        pkg_watt = "N/A"
        pkg_temp = "N/A"

        try:
            out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>/dev/null", shell=True, text=True, timeout=1.5)
            lines = out.strip().split('\\n')
            headers = []
            if lines:
                headers = lines[0].split()

            for line in lines[1:]:
                parts = line.split()
                if not parts:
                    continue

                # Pair header and part, handle cases where lengths mismatch slightly if some columns are empty
                row = dict(zip(headers[:len(parts)], parts))

                if row.get('Core') == '-' and row.get('CPU') == '-':
                    if 'PkgWatt' in row: pkg_watt = row['PkgWatt']
                    if 'PkgTmp' in row: pkg_temp = f"{row['PkgTmp']}°C"
                    continue

                try:
                    cpu_idx = int(row.get('CPU', -1))
                    if cpu_idx >= 0:
                        if 'Avg_MHz' in row: freqs[cpu_idx] = float(row['Avg_MHz'])

                        # In turbostat, 'CoreTmp' only appears on the primary thread of a physical core.
                        # So thread 4 won't have 'CoreTmp' column, or it might be shifted.
                        # We fall back if it is missing by finding the physical core it belongs to later.
                        # Actually turbostat usually prints it for the first thread of the core.
                        # We'll just collect whatever is present.
                        if 'CoreTmp' in row and row['CoreTmp'] != '-':
                            core_temps[cpu_idx] = float(row['CoreTmp'])
                        elif 'Core' in row and row['Core'] != '-':
                            # We can also map physical core temps
                            phys_core = int(row['Core'])
                            if 'CoreTmp' in row:
                                core_temps[phys_core] = float(row['CoreTmp'])

                        states = {}
                        for st in ['C1%', 'C1E%', 'C3%', 'C6%', 'POLL%']:
                            if st in row:
                                try: states[st.replace('%', '')] = float(row[st])
                                except: pass
                        cstates[cpu_idx] = states
                except:
                    pass
        except Exception:
            pass"""

code = code.replace(search_update, replace_update)

search_temps2 = """                temp_text = f" {int(core_temps[i])}°C" if i in core_temps else ""
                core_widget.bar.label_text = f"{freq_text}{temp_text}" """

replace_temps2 = """                # Fallback to map logical threads to physical core temps if turbostat omitted it
                temp_val = None
                if i in core_temps:
                    temp_val = core_temps[i]
                else:
                    phys_cores = self.cpu_count // 2 if self.cpu_count > 4 else self.cpu_count
                    if phys_cores > 0 and (i % phys_cores) in core_temps:
                        temp_val = core_temps[i % phys_cores]

                temp_text = f" {int(temp_val)}°C" if temp_val is not None else ""

                core_widget.bar.label_text = f"{freq_text}{temp_text}" """

code = code.replace(search_temps2, replace_temps2)

with open('local_hardware_monitor_v2_new5.py', 'w') as f:
    f.write(code)
