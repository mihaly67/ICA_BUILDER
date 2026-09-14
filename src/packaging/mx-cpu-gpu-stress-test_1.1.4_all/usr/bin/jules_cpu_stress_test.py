import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QLabel, QPushButton, QHBoxLayout, QTextEdit, QComboBox, QTabWidget, QCheckBox)
from PyQt5.QtCore import Qt, QProcess, QDir
from PyQt5.QtGui import QFont, QIcon, QTextCursor
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

class CPUGPUStressApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jules PC Stress Test - v1.1.4")
        self.setMinimumSize(800, 600)
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
            QComboBox, QCheckBox {
                background-color: #1e293b;
                color: white;
                border: 1px solid #334155;
                padding: 5px;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #000000;
                color: #22c55e;
                font-family: monospace;
                border: 1px solid #334155;
            }
            QTabWidget::pane { border: 1px solid #334155; }
            QTabBar::tab {
                background: #1e293b;
                color: white;
                padding: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: #3b82f6; }
        """)

        # Set KDE Icons (No Tray Icon, Just Window Icon)
        icon_path = "/usr/share/icons/oxygen/base/128x128/apps/utilities-system-monitor.png"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("utilities-system-monitor"))

        # UI Setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("Jules CPU & GPU Stress Test")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        main_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.setup_cpu_tab()
        self.setup_gpu_tab()

    def setup_cpu_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.cpu_status_label = QLabel("Állapot: Készen áll")
        self.cpu_status_label.setStyleSheet("color: #22c55e;")
        layout.addWidget(self.cpu_status_label, alignment=Qt.AlignCenter)

        self.cpu_type_combo = QComboBox()
        self.cpu_type_combo.addItems([
            "Small FFTs (Maximum power, heat, and CPU stress)",
            "Large FFTs (Maximum power and some RAM tested)",
            "Blend (All of the above - tests lots of RAM)"
        ])
        layout.addWidget(self.cpu_type_combo)

        self.cpu_console = QTextEdit()
        self.cpu_console.setReadOnly(True)
        layout.addWidget(self.cpu_console)

        btn_layout = QHBoxLayout()
        self.cpu_start_btn = QPushButton("Prime95 Indítása")
        self.cpu_stop_btn = QPushButton("Leállítás")
        self.cpu_stop_btn.setEnabled(False)

        self.cpu_start_btn.clicked.connect(self.start_cpu_stress)
        self.cpu_stop_btn.clicked.connect(self.stop_cpu_stress)

        btn_layout.addWidget(self.cpu_start_btn)
        btn_layout.addWidget(self.cpu_stop_btn)
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "Prime95 (CPU)")

        self.cpu_process = QProcess()
        self.cpu_process.readyReadStandardOutput.connect(self.handle_cpu_stdout)
        self.cpu_process.readyReadStandardError.connect(self.handle_cpu_stderr)
        self.cpu_process.finished.connect(self.cpu_process_finished)

    def setup_gpu_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        warning_lbl = QLabel("VIGYÁZAT: A GPU teszt hirtelen hőmérsékletemelkedést okoz!\nGyőződj meg róla, hogy a Quadro kártyák hűtése megfelelő.")
        warning_lbl.setStyleSheet("color: #ef4444; font-weight: bold;")
        layout.addWidget(warning_lbl, alignment=Qt.AlignCenter)

        self.gpu_status_label = QLabel("Állapot: Készen áll")
        self.gpu_status_label.setStyleSheet("color: #22c55e;")
        layout.addWidget(self.gpu_status_label, alignment=Qt.AlignCenter)

        self.gpu_preset_combo = QComboBox()
        self.gpu_preset_combo.addItems([
            "Basic (Közepes terhelés - P2000 biztonságos)",
            "Extreme (Maximális terhelés - P4000 ajánlott)"
        ])
        layout.addWidget(self.gpu_preset_combo)

        self.gpu_fullscreen_cb = QCheckBox("Teljes képernyő")
        layout.addWidget(self.gpu_fullscreen_cb)

        self.gpu_console = QTextEdit()
        self.gpu_console.setReadOnly(True)
        layout.addWidget(self.gpu_console)

        btn_layout = QHBoxLayout()
        self.gpu_start_btn = QPushButton("Unigine Heaven Indítása")
        self.gpu_stop_btn = QPushButton("Leállítás")
        self.gpu_stop_btn.setEnabled(False)

        self.gpu_start_btn.clicked.connect(self.start_gpu_stress)
        self.gpu_stop_btn.clicked.connect(self.stop_gpu_stress)

        btn_layout.addWidget(self.gpu_start_btn)
        btn_layout.addWidget(self.gpu_stop_btn)
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "Unigine Heaven (GPU)")

        self.gpu_process = QProcess()
        self.gpu_process.readyReadStandardOutput.connect(self.handle_gpu_stdout)
        self.gpu_process.readyReadStandardError.connect(self.handle_gpu_stderr)
        self.gpu_process.finished.connect(self.gpu_process_finished)

    # --- CPU LOGIC ---
    def write_prime_txt(self, test_type):
        torture_type = 3
        if "Small" in test_type:
            torture_type = 1
        elif "Large" in test_type:
            torture_type = 2

        config_path = os.path.expanduser("~/.jules_mprime")
        if not os.path.exists(config_path):
            os.makedirs(config_path)

        prime_txt = os.path.join(config_path, "prime.txt")
        with open(prime_txt, "w") as f:
            f.write(f"V24OptionsConverted=1\n")
            f.write(f"Torture={torture_type}\n")

        return config_path

    def start_cpu_stress(self):
        mprime_path = "/usr/bin/mprime"
        if not os.path.exists(mprime_path):
            self.cpu_console.append(f"Hiba: Az mprime nem található a {mprime_path} útvonalon!")
            return

        selected_test = self.cpu_type_combo.currentText()
        config_dir = self.write_prime_txt(selected_test)

        self.cpu_process.setWorkingDirectory(config_dir)
        self.cpu_process.start(mprime_path, ["-t"])

        self.cpu_status_label.setText(f"Állapot: PRIME95 FUT ({selected_test})")
        self.cpu_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.cpu_start_btn.setEnabled(False)
        self.cpu_type_combo.setEnabled(False)
        self.cpu_stop_btn.setEnabled(True)
        self.cpu_console.clear()
        self.cpu_console.append(f"--- Prime95 Indítása: {selected_test} ---")

    def stop_cpu_stress(self):
        if self.cpu_process.state() == QProcess.Running:
            self.cpu_process.terminate()
            self.cpu_process.waitForFinished(3000)
            self.cpu_process.kill()

        self.cpu_status_label.setText("Állapot: Leállítva")
        self.cpu_status_label.setStyleSheet("color: #22c55e;")
        self.cpu_start_btn.setEnabled(True)
        self.cpu_type_combo.setEnabled(True)
        self.cpu_stop_btn.setEnabled(False)
        self.cpu_console.append("--- Prime95 Leállítva ---")

    def handle_cpu_stdout(self):
        data = self.cpu_process.readAllStandardOutput()
        self.cpu_console.moveCursor(QTextCursor.End)
        self.cpu_console.insertPlainText(bytes(data).decode("utf8", errors="ignore"))
        self.cpu_console.moveCursor(QTextCursor.End)

    def handle_cpu_stderr(self):
        data = self.cpu_process.readAllStandardError()
        self.cpu_console.moveCursor(QTextCursor.End)
        self.cpu_console.insertPlainText(bytes(data).decode("utf8", errors="ignore"))
        self.cpu_console.moveCursor(QTextCursor.End)

    def cpu_process_finished(self):
        self.stop_cpu_stress()

    # --- GPU LOGIC ---
    def start_gpu_stress(self):
        heaven_path = "/usr/bin/unigine-heaven"
        if not os.path.exists(heaven_path):
            self.gpu_console.append(f"Hiba: A Heaven benchmark nem található a {heaven_path} útvonalon!\nKérlek ellenőrizd a telepítést.")
            return

        is_extreme = "Extreme" in self.gpu_preset_combo.currentText()
        is_fs = self.gpu_fullscreen_cb.isChecked()

        # Build command arguments based on preset
        args = []
        if is_fs:
            args.extend(["-video_fullscreen", "1"])
        else:
            args.extend(["-video_fullscreen", "0", "-video_width", "1280", "-video_height", "720"])

        if is_extreme:
            args.extend(["-extern_preset", "Extreme", "-video_multisample", "8", "-video_app", "opengl"])
        else:
            args.extend(["-extern_preset", "Basic", "-video_multisample", "0", "-video_app", "opengl"])

        self.gpu_process.start(heaven_path, args)

        self.gpu_status_label.setText(f"Állapot: UNIGINE HEAVEN FUT")
        self.gpu_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.gpu_start_btn.setEnabled(False)
        self.gpu_preset_combo.setEnabled(False)
        self.gpu_fullscreen_cb.setEnabled(False)
        self.gpu_stop_btn.setEnabled(True)
        self.gpu_console.clear()
        self.gpu_console.append(f"--- Unigine Heaven Indítása (Extreme: {is_extreme}, FS: {is_fs}) ---")

    def stop_gpu_stress(self):
        if self.gpu_process.state() == QProcess.Running:
            self.gpu_process.terminate()
            self.gpu_process.waitForFinished(3000)
            self.gpu_process.kill()

        self.gpu_status_label.setText("Állapot: Leállítva")
        self.gpu_status_label.setStyleSheet("color: #22c55e;")
        self.gpu_start_btn.setEnabled(True)
        self.gpu_preset_combo.setEnabled(True)
        self.gpu_fullscreen_cb.setEnabled(True)
        self.gpu_stop_btn.setEnabled(False)
        self.gpu_console.append("--- Unigine Heaven Leállítva ---")

    def handle_gpu_stdout(self):
        data = self.gpu_process.readAllStandardOutput()
        self.gpu_console.moveCursor(QTextCursor.End)
        self.gpu_console.insertPlainText(bytes(data).decode("utf8", errors="ignore"))
        self.gpu_console.moveCursor(QTextCursor.End)

    def handle_gpu_stderr(self):
        data = self.gpu_process.readAllStandardError()
        self.gpu_console.moveCursor(QTextCursor.End)
        self.gpu_console.insertPlainText(bytes(data).decode("utf8", errors="ignore"))
        self.gpu_console.moveCursor(QTextCursor.End)

    def gpu_process_finished(self):
        self.stop_gpu_stress()

    def closeEvent(self, event):
        self.stop_cpu_stress()
        self.stop_gpu_stress()
        QApplication.instance().quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    socket = QLocalSocket()
    socket.connectToServer('Jules_CPUGPU_Stress_Test_Instance')
    if socket.waitForConnected(500):
        socket.write(b"SHOW")
        socket.waitForBytesWritten(500)
        sys.exit(0)

    server = QLocalServer()
    server.removeServer('Jules_CPUGPU_Stress_Test_Instance')
    if not server.listen('Jules_CPUGPU_Stress_Test_Instance'):
        sys.exit(1)

    monitor = CPUGPUStressApp()

    def on_new_connection():
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(500)
        conn.readAll()
        monitor.showNormal()
        monitor.activateWindow()

    server.newConnection.connect(on_new_connection)

    monitor.show()
    sys.exit(app.exec_())
