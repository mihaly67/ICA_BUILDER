with open('local_hardware_monitor_v2_new.py', 'r') as f:
    code = f.read()

# Refactor the ResourceBar class to remove its own text rendering entirely and just render the bar + values inside the bar.
# We will create a new composite widget CPUCoreWidget that holds the colored QLabel (the core number) and the ResourceBar.

new_classes = """class ResourceBar(QWidget):
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.label_text = label_text # e.g. "2500MHz 33C"
        self.val1 = 0.0 # Zöld (User)
        self.val2 = 0.0 # Vörös (System/Kernel)
        self.setFixedHeight(15)

    def update_values(self, val1, val2=0.0):
        self.val1 = val1
        self.val2 = val2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1e293b"))
        width = self.rect().width()
        height = self.rect().height()
        total = self.val1 + self.val2
        if total > 100: total = 100
        w1 = int((self.val1 / 100.0) * width)
        w2 = int((self.val2 / 100.0) * width)
        painter.fillRect(0, 0, w1, height, QColor("#16a34a"))
        painter.fillRect(w1, 0, w2, height, QColor("#dc2626"))
        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        # Inside the bar: just the freq/temp and the percentage
        text = f"{self.label_text} [{self.val1+self.val2:.1f}%]"
        painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "  " + text)


class CPUCoreWidget(QWidget):
    def __init__(self, core_idx, parent=None):
        super().__init__(parent)
        self.core_idx = core_idx
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.number_label = QLabel(f"{core_idx}")
        self.number_label.setFixedWidth(20)
        self.number_label.setAlignment(Qt.AlignCenter)
        self.number_label.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")

        self.bar = ResourceBar("")

        layout.addWidget(self.number_label)
        layout.addWidget(self.bar)

    def set_color(self, color):
        self.number_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
"""

# Replace the old ResourceBar entirely
import re
code = re.sub(r'class ResourceBar\(QWidget\):.*?def paintEvent.*?text\)', new_classes + '\n        # dummy', code, flags=re.DOTALL)
# Clean up the dummy hack
code = code.replace('\n        # dummy', '')

# Replace self.cpu_bars references in __init__
search_layout_init = """        for i in range(self.cpu_count):
            bar = ResourceBar(f"CPU {i}")
            self.cpu_bars.append(bar)
            row = i // cols
            col = i % cols
            cpu_layout.addWidget(bar, row, col)"""

replace_layout_init = """        for i in range(self.cpu_count):
            core_widget = CPUCoreWidget(i)
            self.cpu_bars.append(core_widget)
            row = i // cols
            col = i % cols
            cpu_layout.addWidget(core_widget, row, col)"""

code = code.replace(search_layout_init, replace_layout_init)

with open('local_hardware_monitor_v2_new2.py', 'w') as f:
    f.write(code)


with open('local_hardware_monitor_v2_new2.py', 'r') as f:
    code = f.read()

# Update `update_stats` to use `cpupower monitor` and format the text properly
search_update_cpu = """        # Get C-states and frequencies
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

        self.last_cstates = cstates"""

replace_update_cpu = """        # 1.1 Frequencies & Temps
        freqs = {}
        try:
            f = psutil.cpu_freq(percpu=True)
            for i, fr in enumerate(f):
                freqs[i] = fr.current
        except Exception:
            pass

        core_temps = {}
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                for t in temps['coretemp']:
                    if 'Core' in t.label:
                        try:
                            # Parse "Core 0" -> 0
                            c_num = int(t.label.split()[-1])
                            core_temps[c_num] = t.current
                        except:
                            pass
        except:
            pass

        # 1.2 C-States via cpupower monitor
        cstates = {}
        try:
            out = subprocess.check_output("cpupower monitor", shell=True, text=True, stderr=subprocess.DEVNULL)
            lines = out.strip().split('\\n')
            headers = []
            for line in lines:
                if line.strip().startswith("CPU|"):
                    headers = [h.strip() for h in line.replace("||", "|").split("|") if h.strip()]
                elif re.match(r'^\\s*\\d+\\|', line):
                    parts = [p.strip() for p in line.replace("||", "|").split("|") if p.strip()]
                    if len(parts) >= len(headers):
                        cpu_idx = int(parts[0])
                        states = {}
                        for j in range(1, len(headers)):
                            try:
                                states[headers[j]] = float(parts[j].replace(',', '.'))
                            except:
                                pass
                        cstates[cpu_idx] = states
        except Exception:
            pass

        for i, c in enumerate(core_times):
            if i < len(self.cpu_bars):
                core_widget = self.cpu_bars[i]
                core_widget.bar.update_values(c.user, c.system)

                color = "#94a3b8"
                if i in cstates:
                    states = cstates[i]
                    # Find highest percentage
                    if states:
                        active_state = max(states, key=states.get)
                        if "C0" in active_state or "POLL" in active_state:
                            color = "#16a34a" # Green
                        elif active_state in ["C1", "C1E", "C3"]:
                            color = "#eab308" # Yellow
                        elif "C6" in active_state or "C7" in active_state:
                            color = "#64748b" # Gray

                core_widget.set_color(color)

                freq_text = f"{int(freqs[i])}MHz" if i in freqs else ""

                # Temperature mapping for physical cores (e.g. threads 0 and 4 might share Core 0 temp depending on topology)
                # But as an approximation, we map `i` to `i` or `i % physical_cores`
                phys_cores = self.cpu_count // 2 if self.cpu_count > 4 else self.cpu_count
                t_idx = i % phys_cores
                temp_text = f" {int(core_temps[t_idx])}°C" if t_idx in core_temps else ""

                core_widget.bar.label_text = f"{freq_text}{temp_text}" """

import re
code = code.replace(search_update_cpu, replace_update_cpu)

with open('local_hardware_monitor_v2_new2.py', 'w') as f:
    f.write(code)
