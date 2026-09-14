import sys
import os
import psutil
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QPushButton, QProgressBar, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QTextCursor
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

class CleanerWorker(QThread):
    log_update = pyqtSignal(str)
    finished_update = pyqtSignal()

    def __init__(self, mode):
        super().__init__()
        self.mode = mode # "RAM" or "SWAP" or "BOTH"

    def run(self):
        try:
            self.log_update.emit("Tisztítási folyamat indul...")
            if self.mode in ["RAM", "BOTH"]:
                self.log_update.emit("OS Page Cache kiürítése (pkexec sysctl vm.drop_caches=3)...")
                # pkexec brings up a GUI password prompt on MX Linux (Polkit)
                res = subprocess.run(["pkexec", "sysctl", "-w", "vm.drop_caches=3"], capture_output=True, text=True)
                if res.returncode == 0:
                    self.log_update.emit("-> Page Cache sikeresen törölve.")
                else:
                    self.log_update.emit(f"-> Hiba a Page Cache törlésekor: {res.stderr}")

            if self.mode in ["SWAP", "BOTH"]:
                self.log_update.emit("Swap memória újraindítása (ez eltarthat egy ideig)...")
                res = subprocess.run(["pkexec", "swapoff", "-a"], capture_output=True, text=True)
                if res.returncode == 0:
                    self.log_update.emit("-> Swapoff sikeres.")
                    res2 = subprocess.run(["pkexec", "swapon", "-a"], capture_output=True, text=True)
                    if res2.returncode == 0:
                        self.log_update.emit("-> Swapon sikeres, Swap kiürítve.")
                    else:
                        self.log_update.emit(f"-> Hiba a Swapon során: {res2.stderr}")
                else:
                    self.log_update.emit(f"-> Hiba a Swapoff során: {res.stderr}")

        except Exception as e:
            self.log_update.emit(f"Kritikus hiba: {str(e)}")

        self.log_update.emit("Tisztítás befejezve!")
        self.finished_update.emit()

class JulesRAMCleaner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jules RAM & Swap Cleaner - v1.0.0")
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QLabel { color: white; }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #475569; color: #94a3b8; }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 4px;
                text-align: center;
                color: white;
                background-color: #1e293b;
            }
            QProgressBar::chunk { background-color: #22c55e; }
            QTextEdit {
                background-color: #000000;
                color: #3b82f6;
                font-family: monospace;
                border: 1px solid #334155;
            }
        """)

        # Icon
        icon_path = "/usr/share/icons/oxygen/base/128x128/places/user-trash.png"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("user-trash"))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_label = QLabel("Jules RAM & Swap Cleaner")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        main_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        # Status displays
        stats_layout = QHBoxLayout()

        self.ram_label = QLabel("RAM Használat: N/A")
        self.ram_label.setFont(QFont("Segoe UI", 12))
        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)

        self.swap_label = QLabel("Swap Használat: N/A")
        self.swap_label.setFont(QFont("Segoe UI", 12))
        self.swap_bar = QProgressBar()
        self.swap_bar.setRange(0, 100)

        ram_vbox = QVBoxLayout()
        ram_vbox.addWidget(self.ram_label)
        ram_vbox.addWidget(self.ram_bar)

        swap_vbox = QVBoxLayout()
        swap_vbox.addWidget(self.swap_label)
        swap_vbox.addWidget(self.swap_bar)

        stats_layout.addLayout(ram_vbox)
        stats_layout.addLayout(swap_vbox)
        main_layout.addLayout(stats_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_ram = QPushButton("RAM Cache Törlése")
        self.btn_swap = QPushButton("Swap Törlése")
        self.btn_both = QPushButton("Mindkettő Törlése")

        self.btn_ram.clicked.connect(lambda: self.start_clean("RAM"))
        self.btn_swap.clicked.connect(lambda: self.start_clean("SWAP"))
        self.btn_both.clicked.connect(lambda: self.start_clean("BOTH"))

        btn_layout.addWidget(self.btn_ram)
        btn_layout.addWidget(self.btn_swap)
        btn_layout.addWidget(self.btn_both)
        main_layout.addLayout(btn_layout)

        # Log output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        main_layout.addWidget(self.console)

        # Update Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)
        self.update_stats()

        self.worker = None

    def update_stats(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        mem_used_gb = mem.used / (1024**3)
        mem_total_gb = mem.total / (1024**3)
        self.ram_label.setText(f"RAM Használat: {mem_used_gb:.1f} GB / {mem_total_gb:.1f} GB")
        self.ram_bar.setValue(int(mem.percent))

        swap_used_gb = swap.used / (1024**3)
        swap_total_gb = swap.total / (1024**3)
        self.swap_label.setText(f"Swap Használat: {swap_used_gb:.1f} GB / {swap_total_gb:.1f} GB")
        self.swap_bar.setValue(int(swap.percent))

    def set_buttons_enabled(self, state):
        self.btn_ram.setEnabled(state)
        self.btn_swap.setEnabled(state)
        self.btn_both.setEnabled(state)

    def start_clean(self, mode):
        self.set_buttons_enabled(False)
        self.console.append(f"\n--- {mode} TISZTÍTÁS INDÍTÁSA ---")
        self.console.append("Figyelem: A PolicyKit (pkexec) jelszót kérhet a háttérben futó root művelethez!")

        self.worker = CleanerWorker(mode)
        self.worker.log_update.connect(self.append_log)
        self.worker.finished_update.connect(self.clean_finished)
        self.worker.start()

    def append_log(self, text):
        self.console.moveCursor(QTextCursor.End)
        self.console.insertPlainText(text + "\n")
        self.console.moveCursor(QTextCursor.End)

    def clean_finished(self):
        self.set_buttons_enabled(True)
        self.update_stats()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    socket = QLocalSocket()
    socket.connectToServer('Jules_RAM_Cleaner_Instance')
    if socket.waitForConnected(500):
        socket.write(b"SHOW")
        socket.waitForBytesWritten(500)
        sys.exit(0)

    server = QLocalServer()
    server.removeServer('Jules_RAM_Cleaner_Instance')
    if not server.listen('Jules_RAM_Cleaner_Instance'):
        sys.exit(1)

    monitor = JulesRAMCleaner()

    def on_new_connection():
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(500)
        conn.readAll()
        monitor.showNormal()
        monitor.activateWindow()

    server.newConnection.connect(on_new_connection)

    monitor.show()
    sys.exit(app.exec_())
