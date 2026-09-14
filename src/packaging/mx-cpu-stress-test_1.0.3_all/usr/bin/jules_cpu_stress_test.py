import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QLabel, QPushButton, QHBoxLayout, QTextEdit, QComboBox)
from PyQt5.QtCore import Qt, QProcess, QDir
from PyQt5.QtGui import QFont, QIcon, QTextCursor
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

class CPUStressApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jules PC Stress Test - v1.0.3")
        self.setMinimumSize(700, 500)
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
            QTextEdit {
                background-color: #000000;
                color: #22c55e;
                font-family: monospace;
                border: 1px solid #334155;
            }
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
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = QLabel("Jules Prime95 Stress Test")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignCenter)

        self.status_label = QLabel("Állapot: Készen áll")
        self.status_label.setStyleSheet("color: #22c55e;")
        layout.addWidget(self.status_label, alignment=Qt.AlignCenter)

        # Options dropdown for Prime95 Torture Tests
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Small FFTs (Maximum power, heat, and CPU stress)",
            "Large FFTs (Maximum power and some RAM tested)",
            "Blend (All of the above - tests lots of RAM)"
        ])
        layout.addWidget(self.type_combo)

        # Output console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Prime95 Indítása")
        self.stop_btn = QPushButton("Leállítás")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_stress)
        self.stop_btn.clicked.connect(self.stop_stress)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)

        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

    def write_prime_txt(self, test_type):
        # 0 = Custom, 1 = Small FFTs, 2 = In-place large FFTs, 3 = Blend
        torture_type = 3
        if "Small" in test_type:
            torture_type = 1
        elif "Large" in test_type:
            torture_type = 2

        config_path = os.path.expanduser("~/.jules_mprime")
        if not os.path.exists(config_path):
            os.makedirs(config_path)

        # Generate local.txt (mprime automatically reads local.txt/prime.txt in its working dir)
        prime_txt = os.path.join(config_path, "prime.txt")
        with open(prime_txt, "w") as f:
            f.write(f"V24OptionsConverted=1\\n")
            f.write(f"Torture={torture_type}\\n")

        return config_path

    def start_stress(self):
        mprime_path = "/usr/bin/mprime"
        if not os.path.exists(mprime_path):
            self.console.append(f"Hiba: Az mprime nem található a {mprime_path} útvonalon!")
            return

        selected_test = self.type_combo.currentText()
        config_dir = self.write_prime_txt(selected_test)

        self.process.setWorkingDirectory(config_dir)
        self.process.start(mprime_path, ["-t"])

        self.status_label.setText(f"Állapot: PRIME95 FUT ({selected_test})")
        self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.start_btn.setEnabled(False)
        self.type_combo.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.console.clear()
        self.console.append(f"--- Prime95 Indítása: {selected_test} ---")

    def stop_stress(self):
        if self.process.state() == QProcess.Running:
            self.process.terminate()
            self.process.waitForFinished(3000)
            self.process.kill()

        self.status_label.setText("Állapot: Leállítva")
        self.status_label.setStyleSheet("color: #22c55e;")
        self.start_btn.setEnabled(True)
        self.type_combo.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.console.append("--- Prime95 Leállítva ---")

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.console.moveCursor(QTextCursor.End)
        self.console.insertPlainText(stdout)
        self.console.moveCursor(QTextCursor.End)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.console.moveCursor(QTextCursor.End)
        self.console.insertPlainText(stderr)
        self.console.moveCursor(QTextCursor.End)

    def process_finished(self):
        self.stop_stress()

    def closeEvent(self, event):
        self.stop_stress()
        QApplication.instance().quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

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
