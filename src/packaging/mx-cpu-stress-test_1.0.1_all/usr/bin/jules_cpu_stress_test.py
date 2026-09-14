import sys
import multiprocessing
import time
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QLabel, QSystemTrayIcon, QMenu, QAction, QPushButton, QProgressBar, QHBoxLayout, QComboBox)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

def stress_core_cpu():
    while True:
        _ = 3.14159 * 2.71828

def stress_core_memory():
    dummy = []
    while True:
        dummy.extend([0] * 1000000)
        if len(dummy) > 50000000:
            dummy.clear()
        time.sleep(0.01)

def stress_core_io():
    while True:
        with open("/dev/null", "w") as f:
            for _ in range(10000):
                f.write("test data\n")

class StressMonitorWorker(QThread):
    progress_update = pyqtSignal(int)

    def __init__(self, cores, stress_type):
        super().__init__()
        self.cores = cores
        self.stress_type = stress_type
        self.processes = []
        self.running = False

    def run(self):
        self.running = True
        for _ in range(self.cores):
            if self.stress_type == "Memória Erőltetés":
                p = multiprocessing.Process(target=stress_core_memory)
            elif self.stress_type == "I/O Erőltetés":
                p = multiprocessing.Process(target=stress_core_io)
            else:
                p = multiprocessing.Process(target=stress_core_cpu)

            p.daemon = True
            p.start()
            self.processes.append(p)

        elapsed = 0
        while self.running:
            time.sleep(1)
            elapsed += 1
            self.progress_update.emit(elapsed)

    def stop(self):
        self.running = False
        for p in self.processes:
            p.terminate()
        self.processes.clear()

class CPUStressApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jules PC Stress Test - v1.0.1")
        self.setMinimumSize(450, 300)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QLabel { color: white; }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #475569; color: #94a3b8; }
            QComboBox {
                background-color: #1e293b;
                color: white;
                border: 1px solid #334155;
                padding: 5px;
                border-radius: 4px;
            }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 4px;
                text-align: center;
                color: white;
                background-color: #1e293b;
            }
            QProgressBar::chunk {
                background-color: #ef4444;
            }
        """)

        # Set KDE Icons
        icon_path = "/usr/share/icons/oxygen/base/128x128/apps/utilities-system-monitor.png"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("utilities-system-monitor"))

        # Setup System Tray
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(QIcon.fromTheme("utilities-system-monitor"))

        show_action = QAction("Megjelenítés", self)
        hide_action = QAction("Elrejtés", self)
        quit_action = QAction("Bezárás", self)

        show_action.triggered.connect(self.showNormal)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(self.quit_app)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.tray_icon.show()

        # UI Setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = QLabel("Jules PC Stress Test")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignCenter)

        self.status_label = QLabel("Állapot: Készen áll")
        self.status_label.setStyleSheet("color: #22c55e;")
        layout.addWidget(self.status_label, alignment=Qt.AlignCenter)

        # Options dropdown
        self.type_combo = QComboBox()
        self.type_combo.addItems(["CPU (Matematikai)", "Memória Erőltetés", "I/O Erőltetés"])
        layout.addWidget(self.type_combo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # indeterminate until started
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.time_label = QLabel("0 másodperc telt el")
        layout.addWidget(self.time_label, alignment=Qt.AlignCenter)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Stress Test Indítása")
        self.stop_btn = QPushButton("Leállítás")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_stress)
        self.stop_btn.clicked.connect(self.stop_stress)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)

        self.worker = None

    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def start_stress(self):
        cores = multiprocessing.cpu_count()
        stress_type = self.type_combo.currentText()

        self.worker = StressMonitorWorker(cores, stress_type)
        self.worker.progress_update.connect(self.update_time)
        self.worker.start()

        self.status_label.setText(f"Állapot: STRESSZ FUT ({cores} magon) - {stress_type}")
        self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.start_btn.setEnabled(False)
        self.type_combo.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.progress_bar.setRange(0, 0) # Indeterminate spinning

    def stop_stress(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None

        self.status_label.setText("Állapot: Leállítva")
        self.status_label.setStyleSheet("color: #22c55e;")
        self.start_btn.setEnabled(True)
        self.type_combo.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def update_time(self, seconds):
        self.time_label.setText(f"{seconds} másodperc telt el")

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Stress Test",
            "Az alkalmazás a tálcára került.",
            QSystemTrayIcon.Information,
            2000
        )

    def quit_app(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        QApplication.instance().quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setQuitOnLastWindowClosed(False)

    socket = QLocalSocket()
    socket.connectToServer('Jules_Stress_Test_Instance')
    if socket.waitForConnected(500):
        socket.write(b"SHOW")
        socket.waitForBytesWritten(500)
        sys.exit(0)

    server = QLocalServer()
    server.removeServer('Jules_Stress_Test_Instance')
    if not server.listen('Jules_Stress_Test_Instance'):
        sys.exit(1)

    monitor = CPUStressApp()

    def on_new_connection():
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(500)
        conn.readAll()
        monitor.showNormal()
        monitor.activateWindow()

    server.newConnection.connect(on_new_connection)

    monitor.show()
    sys.exit(app.exec_())
