import re
with open('local_hardware_monitor_v2.py', 'r') as f:
    code = f.read()

# Step 1: Replace CPU Layout with Grid Layout
search_cpu_layout = """        cpu_layout = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()
        for i in range(self.cpu_count):
            bar = ResourceBar(f"{i+1}")
            self.cpu_bars.append(bar)
            if i % 2 == 0:
                col1.addWidget(bar)
            else:
                col2.addWidget(bar)
        cpu_layout.addLayout(col1)
        cpu_layout.addLayout(col2)
        self.layout.addLayout(cpu_layout)"""

replace_cpu_layout = """        from PyQt5.QtWidgets import QGridLayout
        cpu_layout = QGridLayout()
        # Determine number of columns dynamically (e.g. 2, 4, 8)
        if self.cpu_count <= 8:
            cols = 2
        elif self.cpu_count <= 20:
            cols = 4
        else:
            cols = 8

        for i in range(self.cpu_count):
            # C-State based color support will change this label later dynamically
            bar = ResourceBar(f"CPU {i}")
            self.cpu_bars.append(bar)
            row = i // cols
            col = i % cols
            cpu_layout.addWidget(bar, row, col)

        self.layout.addLayout(cpu_layout)"""

code = code.replace(search_cpu_layout, replace_cpu_layout)

with open('local_hardware_monitor_v2_new.py', 'w') as f:
    f.write(code)


search_legend = """        legend_lbl = QLabel("Jelmagyarázat: [Zöld=Használt] [Kék=Puffer] [Sárga=Cache] | CPU: [Zöld=User] [Vörös=Sys]")"""

replace_legend = """        legend_lbl = QLabel("Jelmagyarázat: Mem: [Zöld=Használt] [Kék=Puffer] [Sárga=Cache] | CPU Terhelés: [Zöld=User] [Vörös=Sys]\\n"
                            "CPU C-State: [Zöld=C0 (Aktív)] [Sárga=C1/C1E/C3 (Pihen)] [Szürke=C6/Alvó (Kikapcsolt)]")"""

with open('local_hardware_monitor_v2_new.py', 'r') as f:
    code = f.read()
code = code.replace(search_legend, replace_legend)

# Adding Total Temps and Power placeholder in `stats_header` area
search_stats = """        self.stats_header = QLabel("Uptime: N/A  |  Load average: N/A  |  Tasks: N/A")
        self.stats_header.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 13px; margin-bottom: 5px;")
        self.layout.addWidget(self.stats_header)"""

replace_stats = """        self.stats_header = QLabel("Uptime: N/A  |  Load average: N/A  |  Tasks: N/A")
        self.stats_header.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 13px;")
        self.layout.addWidget(self.stats_header)

        self.sensor_header = QLabel("Hőmérséklet: N/A  |  Teljesítmény (Watt): N/A")
        self.sensor_header.setStyleSheet("color: #f87171; font-weight: bold; font-size: 13px; margin-bottom: 5px;")
        self.layout.addWidget(self.sensor_header)"""

code = code.replace(search_stats, replace_stats)

with open('local_hardware_monitor_v2_new.py', 'w') as f:
    f.write(code)
# Modify update_stats for CPU freq and temp
search_cpu_update = """        core_times = psutil.cpu_times_percent(percpu=True)
        for i, c in enumerate(core_times):
            if i < len(self.cpu_bars):
                self.cpu_bars[i].update_values(c.user, c.system)"""

replace_cpu_update = """        core_times = psutil.cpu_times_percent(percpu=True)

        # Get C-states and frequencies
        cstates = {}
        try:
            for i in range(self.cpu_count):
                base = f"/sys/devices/system/cpu/cpu{i}/cpuidle"
                if not os.path.exists(base): continue
                c_states_time = {}
                for s in os.listdir(base):
                    if s.startswith("state"):
                        name = open(f"{base}/{s}/name").read().strip()
                        t = int(open(f"{base}/{s}/time").read().strip())
                        c_states_time[name] = t
                cstates[i] = c_states_time
        except Exception:
            pass

        freqs = {}
        try:
            f = psutil.cpu_freq(percpu=True)
            for i, fr in enumerate(f):
                freqs[i] = fr.current
        except Exception:
            pass

        # Calculate C-state deltas (simplistic approach: just check active states based on delta next tick)
        if not hasattr(self, 'last_cstates'):
            self.last_cstates = cstates

        for i, c in enumerate(core_times):
            if i < len(self.cpu_bars):
                # Update bar usage
                self.cpu_bars[i].update_values(c.user, c.system)

                # Determine C-state color
                color = "#94a3b8" # Default Gray / Sleeping
                active_state = "C6"

                if i in cstates and i in self.last_cstates:
                    deltas = {}
                    for k in cstates[i]:
                        deltas[k] = cstates[i][k] - self.last_cstates[i].get(k, 0)

                    if deltas:
                        # Find the state with the maximum increase
                        active_state = max(deltas, key=deltas.get)
                        if active_state == "C0" or "POLL" in active_state:
                            color = "#16a34a" # Green
                        elif active_state in ["C1", "C1E", "C3"]:
                            color = "#eab308" # Yellow
                        elif "C6" in active_state or "C7" in active_state:
                            color = "#64748b" # Gray

                # Update text
                freq_text = f" {int(freqs[i])}MHz" if i in freqs else ""
                self.cpu_bars[i].label_text = f"CPU {i}{freq_text}"
                self.cpu_bars[i].label_color = color

        self.last_cstates = cstates

        # Sensor updates
        temp_str = "N/A"
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                pkg = next((t for t in temps['coretemp'] if 'Package' in t.label), None)
                if pkg:
                    temp_str = f"{pkg.current}°C"
                else:
                    temp_str = f"{temps['coretemp'][0].current}°C"
        except:
            pass

        self.sensor_header.setText(f"Hőmérséklet (CPU): {temp_str}  |  Teljesítmény: ~ N/A Watt (Készül)")"""

with open('local_hardware_monitor_v2_new.py', 'r') as f:
    code = f.read()
code = code.replace(search_cpu_update, replace_cpu_update)

with open('local_hardware_monitor_v2_new.py', 'w') as f:
    f.write(code)
# Fix ResourceBar to accept and use `label_color`
search_resourcebar = """class ResourceBar(QWidget):
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.val1 = 0.0 # Zöld (User)
        self.val2 = 0.0 # Vörös (System/Kernel)
        self.setFixedHeight(15)"""

replace_resourcebar = """class ResourceBar(QWidget):
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.label_color = "white"
        self.val1 = 0.0 # Zöld (User)
        self.val2 = 0.0 # Vörös (System/Kernel)
        self.setFixedHeight(15)"""

search_paint = """        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        text = f"{self.label_text} [{self.val1+self.val2:.1f}%]"
        painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "  " + text)"""

replace_paint = """        painter.setPen(QColor(self.label_color))
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        text = f"{self.label_text} [{self.val1+self.val2:.1f}%]"
        painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "  " + text)"""

with open('local_hardware_monitor_v2_new.py', 'r') as f:
    code = f.read()
code = code.replace(search_resourcebar, replace_resourcebar)
code = code.replace(search_paint, replace_paint)
with open('local_hardware_monitor_v2_new.py', 'w') as f:
    f.write(code)
