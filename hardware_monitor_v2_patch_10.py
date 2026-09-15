with open('local_hardware_monitor_v2_new7.py', 'r') as f:
    code = f.read()

# Instead of blocking the UI thread waiting for 5 seconds for turbostat (which hangs the GUI entirely),
# we need to decouple turbostat fetching into a background thread or completely asynchronous process.
# We will use QThread and QTimer.

add_imports = """from PyQt5.QtCore import QThread, pyqtSignal, QTimer"""
if "QThread" not in code:
    code = code.replace("from PyQt5.QtCore import QTimer", "from PyQt5.QtCore import QTimer, QThread, pyqtSignal")

turbostat_worker_code = """
class TurbostatWorker(QThread):
    data_ready = pyqtSignal(dict, dict, dict, str, str) # freqs, core_temps, cstates, pkg_watt, pkg_temp

    def run(self):
        while True:
            freqs = {}
            core_temps = {}
            cstates = {}
            pkg_watt = "N/A"
            pkg_temp = "N/A"
            try:
                # Turbostat can take a few seconds
                out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>&1", shell=True, text=True, timeout=10)
                lines = out.strip().split('\\n')
                headers = []
                header_idx = -1
                for i, line in enumerate(lines):
                    if 'Core' in line and 'CPU' in line and 'Avg_MHz' in line:
                        header_idx = i
                        break

                if header_idx != -1:
                    header_line = lines[header_idx].split('] Jules jelszava: ')[-1]
                    headers = header_line.split()
                    for line in lines[header_idx+1:]:
                        parts = line.split()
                        if not parts: continue
                        row = dict(zip(headers[:len(parts)], parts))

                        if row.get('Core') == '-' and row.get('CPU') == '-':
                            if 'PkgWatt' in row: pkg_watt = row['PkgWatt']
                            if 'PkgTmp' in row: pkg_temp = f"{row['PkgTmp']}°C"
                            continue

                        try:
                            cpu_idx = int(row.get('CPU', -1))
                            if cpu_idx >= 0:
                                if 'Avg_MHz' in row: freqs[cpu_idx] = float(row['Avg_MHz'])

                                if 'CoreTmp' in row and row['CoreTmp'] != '-':
                                    core_temps[cpu_idx] = float(row['CoreTmp'])
                                elif 'Core' in row and row['Core'] != '-':
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
                pass

            self.data_ready.emit(freqs, core_temps, cstates, pkg_watt, pkg_temp)
            import time
            time.sleep(1) # Wait before polling again

"""

# Insert the worker class definition before HardwareMonitor class
search_hw_monitor = "class HardwareMonitor(QMainWindow):"
code = code.replace(search_hw_monitor, turbostat_worker_code + search_hw_monitor)

# Set up the thread inside HardwareMonitor __init__
search_timer_init = """        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)"""

replace_timer_init = """        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)

        # Latest Turbostat data placeholders
        self.ts_freqs = {}
        self.ts_core_temps = {}
        self.ts_cstates = {}
        self.ts_pkg_watt = "N/A"
        self.ts_pkg_temp = "N/A"

        # Start background turbostat poller
        self.ts_worker = TurbostatWorker()
        self.ts_worker.data_ready.connect(self.update_turbostat_data)
        self.ts_worker.start()"""

code = code.replace(search_timer_init, replace_timer_init)

# Add the slot
search_closeEvent = """    def closeEvent(self, event):"""
replace_closeEvent = """    def update_turbostat_data(self, freqs, core_temps, cstates, pkg_watt, pkg_temp):
        self.ts_freqs = freqs
        self.ts_core_temps = core_temps
        self.ts_cstates = cstates
        self.ts_pkg_watt = pkg_watt
        self.ts_pkg_temp = pkg_temp

    def closeEvent(self, event):"""
code = code.replace(search_closeEvent, replace_closeEvent)


# Clean out the blocking turbostat logic from update_stats
search_update_stats_old_turbostat = """        # 1.1 Frequencies, Temps, C-States via turbostat
        freqs = {}
        core_temps = {}
        cstates = {}
        pkg_watt = "N/A"
        pkg_temp = "N/A"

        try:
            out = subprocess.check_output("echo '1104' | sudo -S /usr/sbin/turbostat -q --num_iterations 1 2>&1", shell=True, text=True, timeout=5)
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
                lines = lines[header_idx+1:]

            for line in lines:
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


replace_update_stats_new_turbostat = """        # Use cached background Turbostat data
        freqs = self.ts_freqs
        core_temps = self.ts_core_temps
        cstates = self.ts_cstates
        pkg_watt = self.ts_pkg_watt
        pkg_temp = self.ts_pkg_temp"""

code = code.replace(search_update_stats_old_turbostat, replace_update_stats_new_turbostat)


with open('local_hardware_monitor_v2_new8.py', 'w') as f:
    f.write(code)
