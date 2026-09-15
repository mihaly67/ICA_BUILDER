import threading
import sys
import psutil
import subprocess
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QTableView, QHeaderView,
                             QAbstractItemView, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import QTimer, Qt, QAbstractTableModel, QSortFilterProxyModel, QModelIndex, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont, QPainter, QIcon
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

class ResourceBar(QWidget):
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

class MultiBar(QWidget):
    def __init__(self, label_text, color_map, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.color_map = color_map
        self.setFixedHeight(15)
        self.text_override = ""

    def update_values(self, color_map, text_override=""):
        self.color_map = color_map
        self.text_override = text_override
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1e293b"))
        width = self.rect().width()
        height = self.rect().height()
        current_x = 0
        for color_hex, val_pct in self.color_map:
            w = int((val_pct / 100.0) * width)
            if w > 0:
                painter.fillRect(current_x, 0, w, height, QColor(color_hex))
                current_x += w
        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        text = self.text_override if self.text_override else self.label_text
        painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "  " + text)

# --- Custom Table Model for Smooth Scrolling and Proper Sorting ---
class ProcessTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or [] # List of dicts: [{'name': '...', 'pid': 123, 'cpu': 1.5, 'ram': 0.5}]
        self.headers = ["Név / Argumentumok", "PID", "CPU %", "RAM %"]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        item = self._data[row]

        # Sorter uses UserRole for numeric sorting
        if role == Qt.UserRole:
            if col == 0: return item['name'].lower()
            if col == 1: return item['pid']
            if col == 2: return item['cpu']
            if col == 3: return item['ram']

        if role == Qt.DisplayRole:
            if col == 0: return item['name']
            if col == 1: return str(item['pid'])
            if col == 2: return f"{item['cpu']:.1f}"
            if col == 3: return f"{item['ram']:.1f}"

        if role == Qt.TextAlignmentRole:
            if col > 0: return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class TurbostatWorker(QObject):
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
                import subprocess
                out = subprocess.check_output("sudo -n /usr/sbin/turbostat -q --num_iterations 1 2>&1", shell=True, text=True, timeout=10)
                lines = out.strip().split('\n')
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
                                for st in ['Busy%', 'C1%', 'C1E%', 'C3%', 'C6%', 'POLL%']:
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

class HardwareMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hardver Monitor (Htop + Nvtop)")
        self.resize(1000, 800)
        self.setStyleSheet("QMainWindow { background-color: #0f172a; color: white; }")

        # Ablak ikon (Pajzs)
        self.icon_path = "/usr/share/icons/gnome/256x256/apps/utilities-system-monitor.png"
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("utilities-system-monitor"))

        # Tray Icon beállítás
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(self.icon_path):
            self.tray_icon.setIcon(QIcon(self.icon_path))
        else:
            self.tray_icon.setIcon(QIcon.fromTheme("utilities-system-monitor"))

        tray_menu = QMenu()
        show_action = QAction("Megjelenítés", self)
        quit_action = QAction("Bezárás", self)
        show_action.triggered.connect(self.showNormal)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.tray_icon.show()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- Felső statisztikák (Htop stílus) ---
        self.stats_header = QLabel("Uptime: N/A  |  Load average: N/A  |  Tasks: N/A")
        self.stats_header.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 13px;")
        self.layout.addWidget(self.stats_header)

        self.sensor_header = QLabel("Hőmérséklet: N/A  |  Teljesítmény (Watt): N/A")
        self.sensor_header.setStyleSheet("color: #f87171; font-weight: bold; font-size: 13px; margin-bottom: 5px;")
        self.layout.addWidget(self.sensor_header)

        # --- CPU Szekció ---
        self.cpu_bars = []
        self.cpu_count = psutil.cpu_count()

        cpu_header = QLabel(f"CPU Terhelés (Magok száma: {self.cpu_count})")
        cpu_header.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px;")
        self.layout.addWidget(cpu_header)

        self.total_cpu_bar = ResourceBar("CPU Összesített")
        self.layout.addWidget(self.total_cpu_bar)

        from PyQt5.QtWidgets import QGridLayout
        cpu_layout = QGridLayout()

        # Calculate dynamic columns: max 5 rows, then expand columns
        cols = max(2, (self.cpu_count + 4) // 5)

        for i in range(self.cpu_count):
            core_widget = CPUCoreWidget(i)
            self.cpu_bars.append(core_widget)
            row = i // cols
            col = i % cols
            cpu_layout.addWidget(core_widget, row, col)

        self.layout.addLayout(cpu_layout)

        # --- Memória és Swap ---
        mem_layout = QVBoxLayout()
        legend_lbl = QLabel("Jelmagyarázat: Mem: [Zöld=Használt] [Kék=Puffer] [Sárga=Cache] | CPU Terhelés: [Zöld=User] [Vörös=Sys]\n"
                            "CPU C-State: [Zöld=C0 (Aktív)] [Sárga=C1/C1E/C3 (Pihen)] [Szürke=C6/Alvó (Kikapcsolt)]")
        legend_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        mem_layout.addWidget(legend_lbl)

        self.mem_bar = MultiBar("Mem", [])
        self.swap_bar = MultiBar("Swp", [])
        mem_layout.addWidget(self.mem_bar)
        mem_layout.addWidget(self.swap_bar)
        self.layout.addLayout(mem_layout)

        # --- GPU Szekció ---
        gpu_header = QLabel("GPU & VRAM (NVIDIA)")
        gpu_header.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.layout.addWidget(gpu_header)

        self.gpu_bar = ResourceBar("GPU Mag")
        self.vram_bar = ResourceBar("VRAM")
        self.layout.addWidget(self.gpu_bar)
        self.layout.addWidget(self.vram_bar)

        # --- Processzek (Smooth TableView) ---
        proc_header = QLabel("Folyamatok (Processzek)")
        proc_header.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.layout.addWidget(proc_header)

        self.table_view = QTableView()
        self.table_model = ProcessTableModel()

        # Proxy for sorting
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setSortRole(Qt.UserRole)

        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSortingEnabled(True)

        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.table_view.setStyleSheet("""
            QTableView { background-color: #1e293b; color: white; gridline-color: #334155; border: none; }
            QHeaderView::section { background-color: #0f172a; color: #94a3b8; font-weight: bold; border: 1px solid #334155; }
        """)

        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_process_menu)

        self.layout.addWidget(self.table_view)

        self.process_cache = {}

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)

        # Start background turbostat poller
        self.ts_worker = TurbostatWorker()
        self.ts_worker.data_ready.connect(self.update_turbostat_data)
        self.ts_thread = threading.Thread(target=self.ts_worker.run, daemon=True)
        self.ts_thread.start()



        # Latest Turbostat data placeholders
        self.ts_freqs = {}
        self.ts_core_temps = {}
        self.ts_cstates = {}
        self.ts_pkg_watt = "N/A"
        self.ts_pkg_temp = "N/A"



        # Latest Turbostat data placeholders
        self.ts_freqs = {}
        self.ts_core_temps = {}
        self.ts_cstates = {}
        self.ts_pkg_watt = "N/A"
        self.ts_pkg_temp = "N/A"



        self.update_stats()
        self.table_view.sortByColumn(0, Qt.AscendingOrder) # Default ABC

    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()



    def update_turbostat_data(self, freqs, core_temps, cstates, pkg_watt, pkg_temp):
        self.ts_freqs = freqs
        self.ts_core_temps = core_temps
        self.ts_cstates = cstates
        self.ts_pkg_watt = pkg_watt
        self.ts_pkg_temp = pkg_temp

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("Hardver Monitor", "Az alkalmazás a tálcán fut tovább.", QSystemTrayIcon.Information, 2000)

    def show_process_menu(self, pos):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        # Retrieve the PID from the proxy model
        pid_index = self.proxy_model.index(row, 1)
        name_index = self.proxy_model.index(row, 0)

        pid = int(self.proxy_model.data(pid_index, Qt.DisplayRole))
        name = self.proxy_model.data(name_index, Qt.DisplayRole)

        menu = QMenu(self)
        kill_action = QAction(f"Kill Process ({name} - PID: {pid})", self)

        def kill_process():
            try:
                # Basic kill attempt
                p = psutil.Process(pid)
                p.kill()
                self.tray_icon.showMessage("Hardver Monitor", f"Folyamat bezárva: {name}", QSystemTrayIcon.Information, 2000)
            except psutil.AccessDenied:
                # If access is denied, use pkexec for sudo kill
                try:
                    subprocess.Popen(f"pkexec kill -9 {pid}", shell=True)
                except:
                    pass
            except Exception:
                pass

        kill_action.triggered.connect(kill_process)
        menu.addAction(kill_action)
        menu.exec_(self.table_view.viewport().mapToGlobal(pos))

    def get_uptime(self):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            hours, rem = divmod(uptime_seconds, 3600)
            minutes, _ = divmod(rem, 60)
            return f"{int(hours):02d}:{int(minutes):02d}:{int(_):02d}"
        except:
            return "N/A"

    def get_loadavg(self):
        try:
            avg1, avg5, avg15 = os.getloadavg()
            return f"{avg1:.2f} {avg5:.2f} {avg15:.2f}"
        except:
            return "N/A"

    def update_stats(self):
        # 0. Felső Statisztika
        try:
            tasks_total = len(psutil.pids())
            running = len([p for p in psutil.process_iter(['status']) if p.info.get('status') == psutil.STATUS_RUNNING])
            uptime = self.get_uptime()
            loadavg = self.get_loadavg()
            self.stats_header.setText(f"Uptime: {uptime}  |  Load average: {loadavg}  |  Tasks: {tasks_total}, {running} running")
        except:
            pass

        # 1. CPU Frissítés
        total_times = psutil.cpu_times_percent(percpu=False)
        self.total_cpu_bar.update_values(total_times.user, total_times.system)

        core_times = psutil.cpu_times_percent(percpu=True)

        # Use cached background Turbostat data
        freqs = self.ts_freqs
        core_temps = self.ts_core_temps
        cstates = self.ts_cstates
        pkg_watt = self.ts_pkg_watt
        pkg_temp = self.ts_pkg_temp

        for i, c in enumerate(core_times):
            if i < len(self.cpu_bars):
                core_widget = self.cpu_bars[i]
                core_widget.bar.update_values(c.user, c.system)

                color = "#94a3b8"
                if i in cstates:
                    states = cstates[i]
                    # states dict has 'C1', 'C1E', 'C3', 'C6', 'POLL', and 'Busy'
                    # Actually turbostat dict above didn't parse Busy%! Let's parse 'Busy%' as 'C0'.
                    if states:
                        active_state = max(states, key=states.get)
                        if active_state in ["C0", "Busy", "POLL"]:
                            color = "#16a34a" # Green (Aktív)
                        elif active_state in ["C1", "C1E", "C3"]:
                            color = "#eab308" # Yellow (Készenlét/Pihen)
                        elif "C6" in active_state or "C7" in active_state:
                            color = "#64748b" # Gray (Kikapcsolt/Alvó)

                core_widget.set_color(color)

                freq_text = f"{int(freqs[i])}MHz" if i in freqs else ""

                # Fallback to map logical threads to physical core temps if turbostat omitted it
                temp_val = None
                if i in core_temps:
                    temp_val = core_temps[i]
                else:
                    phys_cores = self.cpu_count // 2 if self.cpu_count > 4 else self.cpu_count
                    if phys_cores > 0 and (i % phys_cores) in core_temps:
                        temp_val = core_temps[i % phys_cores]

                temp_text = f" {int(temp_val)}°C" if temp_val is not None else ""

                core_widget.bar.label_text = f"{freq_text}{temp_text}"

        self.sensor_header.setText(f"Hőmérséklet (CPU): {pkg_temp}  |  Teljesítmény: {pkg_watt} W")

        # 1.5 Memória és SWAP
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        mem_used_pct = (mem.used / mem.total) * 100
        mem_buff_pct = (getattr(mem, 'buffers', 0) / mem.total) * 100
        mem_cach_pct = (getattr(mem, 'cached', 0) / mem.total) * 100

        mem_colors = [
            ("#16a34a", mem_used_pct),
            ("#2563eb", mem_buff_pct),
            ("#eab308", mem_cach_pct),
        ]
        used_gb = mem.used / (1024**3)
        total_gb = mem.total / (1024**3)
        self.mem_bar.update_values(mem_colors, f"Mem [{used_gb:.1f}G / {total_gb:.1f}G]")

        swap_used_pct = (swap.used / swap.total) * 100 if swap.total > 0 else 0
        swap_colors = [("#dc2626", swap_used_pct)]
        swap_gb = swap.used / (1024**3)
        swap_tot_gb = swap.total / (1024**3)
        self.swap_bar.update_values(swap_colors, f"Swp [{swap_gb:.1f}G / {swap_tot_gb:.1f}G]")

        # 2. GPU Frissítés
        try:
            cmd = "nvidia-smi --query-gpu=utilization.gpu,utilization.memory --format=csv,noheader,nounits"
            output = subprocess.check_output(cmd, shell=True, text=True).strip()
            if output:
                parts = output.split(',')
                if len(parts) >= 2:
                    self.gpu_bar.update_values(float(parts[0].strip()))
                    self.vram_bar.update_values(float(parts[1].strip()))
        except Exception:
            self.gpu_bar.update_values(0)
            self.vram_bar.update_values(0)
            self.gpu_bar.label_text = "GPU (Nem elérhető)"

        # 3. Processzek Frissítése
        new_data = []
        current_pids = set()

        for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent']):
            try:
                info = p.info
                pid = info['pid']
                current_pids.add(pid)

                if pid not in self.process_cache:
                    self.process_cache[pid] = p
                    p.cpu_percent(interval=None)
                    cpu = 0.0
                else:
                    cpu = self.process_cache[pid].cpu_percent(interval=None)

                cpu = cpu / self.cpu_count

                cmdline = info.get('cmdline')
                if cmdline:
                    name = " ".join(cmdline)
                else:
                    name = info.get('name', 'Ismeretlen')

                ram = info.get('memory_percent', 0.0) or 0.0

                new_data.append({'name': name, 'pid': pid, 'cpu': cpu, 'ram': ram})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Cache takarítás
        pids_to_remove = set(self.process_cache.keys()) - current_pids
        for pid in pids_to_remove:
            del self.process_cache[pid]

        # Update Table Model (this triggers the view to update without losing scroll position/sorting)
        self.table_model.update_data(new_data)

# Server logikát beépítjük, hogy QSystemTrayIconnal is mukodjön.
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setQuitOnLastWindowClosed(False) # Hogy fusson a tálcán

    # Singleton check
    socket = QLocalSocket()
    socket.connectToServer('Jules_HW_Monitor_Instance')
    if socket.waitForConnected(500):
        # Már fut!
        socket.write(b"SHOW")
        if socket.waitForBytesWritten(500):
            sys.exit(0)

    # Ha döglött a socket, töröljük
    QLocalServer.removeServer('Jules_HW_Monitor_Instance')

    server = QLocalServer()
    server.removeServer('Jules_HW_Monitor_Instance')
    if not server.listen('Jules_HW_Monitor_Instance'):
        print(f"Failed to listen on socket: {server.errorString()}")
        sys.exit(1)

    window = HardwareMonitor()

    # Ha kap egy SHOW üzenetet a szerver a másik klienstől
    def on_new_connection():
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(500)
        conn.readAll()
        window.showNormal()
        window.activateWindow()

    server.newConnection.connect(on_new_connection)

    if "--hidden" not in sys.argv:
        window.show()

    sys.exit(app.exec_())
