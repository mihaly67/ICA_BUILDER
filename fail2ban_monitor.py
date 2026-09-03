import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

class Fail2banMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.update_statuses()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_statuses)
        self.timer.start(5000)

    def initUI(self):
        self.setWindowTitle('Fail2ban Monitor')
        self.setMinimumSize(400, 150)

        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #e0e0e0; }
            QFrame { border: 1px solid #555; border-radius: 5px; background-color: #3b3b3b; }
            QLabel { border: none; }
            QPushButton { background-color: #4b4b4b; border: 1px solid #777; border-radius: 3px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #5b5b5b; }
            QPushButton:disabled { background-color: #3b3b3b; color: #777; }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        frame = QFrame()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Fail2ban Tűzfal")
        title.setFont(QFont('Arial', 12, QFont.Bold))

        self.status_lbl = QLabel("ÁLLAPOT: ISMERETLEN")
        self.status_lbl.setFont(QFont('Arial', 10, QFont.Bold))

        self.btn_start = QPushButton("Indítás")
        self.btn_stop = QPushButton("Leállítás")

        # A /etc/sudoers.d/security_center-ben systemctl parancsok vannak engedélyezve
        self.btn_start.clicked.connect(lambda: self.run_cmd_sudo("sudo /usr/bin/systemctl start fail2ban"))
        self.btn_stop.clicked.connect(lambda: self.run_cmd_sudo("sudo /usr/bin/systemctl stop fail2ban"))

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.status_lbl)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)

        frame.setLayout(layout)
        main_layout.addWidget(frame)
        self.setLayout(main_layout)

    def run_cmd_sudo(self, cmd):
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            QTimer.singleShot(1000, self.update_statuses)
        except Exception as e:
            print(f"Error: {e}")

    def check_service(self):
        try:
            # sysvinit rendszeren a systemctl status lehet nem működik megbízhatóan sudo nélkül
            res = subprocess.run("service fail2ban status", shell=True, capture_output=True, text=True)
            return "running" in res.stdout.lower() or "active" in res.stdout.lower()
        except:
            return False

    def update_statuses(self):
        is_active = self.check_service()
        if is_active:
            self.status_lbl.setText("AKTÍV")
            self.status_lbl.setStyleSheet("color: #66BB6A; font-weight: bold;")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        else:
            self.status_lbl.setText("INAKTÍV")
            self.status_lbl.setStyleSheet("color: #9E9E9E; font-weight: bold;")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = Fail2banMonitor()
    monitor.show()
    sys.exit(app.exec_())
