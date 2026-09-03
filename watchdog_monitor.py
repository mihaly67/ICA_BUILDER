import sys
import subprocess
import tempfile
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

class WatchdogMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.update_statuses()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_statuses)
        self.timer.start(5000)

    def initUI(self):
        self.setWindowTitle('Watchdog Monitor')
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

        title = QLabel("Merkava Watchdog")
        title.setFont(QFont('Arial', 12, QFont.Bold))

        self.status_lbl = QLabel("ÁLLAPOT: ISMERETLEN")
        self.status_lbl.setFont(QFont('Arial', 10, QFont.Bold))

        self.btn_start = QPushButton("Indítás")
        self.btn_stop = QPushButton("Leállítás")

        self.btn_start.clicked.connect(self.start_watchdog)
        self.btn_stop.clicked.connect(self.stop_watchdog)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.status_lbl)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)

        frame.setLayout(layout)
        main_layout.addWidget(frame)
        self.setLayout(main_layout)

    def start_watchdog(self):
        try:
            res = subprocess.run(['sudo', '/usr/bin/crontab', '-l'], capture_output=True, text=True)
            current_cron = [line for line in res.stdout.split('\n') if line and 'miner_watchdog' not in line]
            current_cron.append('* * * * * /usr/local/bin/miner_watchdog.sh')
            new_cron = '\n'.join(current_cron) + '\n'

            process = subprocess.Popen(['sudo', '/usr/bin/crontab', '-'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.communicate(input=new_cron.encode())

            QTimer.singleShot(1000, self.update_statuses)
        except Exception as e:
            print(f"Error: {e}")

    def stop_watchdog(self):
        try:
            res = subprocess.run(['sudo', '/usr/bin/crontab', '-l'], capture_output=True, text=True)
            current_cron = [line for line in res.stdout.split('\n') if line and 'miner_watchdog' not in line]
            new_cron = '\n'.join(current_cron) + '\n'

            process = subprocess.Popen(['sudo', '/usr/bin/crontab', '-'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.communicate(input=new_cron.encode())

            QTimer.singleShot(1000, self.update_statuses)
        except Exception as e:
            print(f"Error: {e}")

    def check_cron(self):
        try:
            res = subprocess.run(['sudo', '/usr/bin/crontab', '-l'], capture_output=True, text=True)
            return "miner_watchdog.sh" in res.stdout
        except:
            return False

    def update_statuses(self):
        is_active = self.check_cron()
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
    monitor = WatchdogMonitor()
    monitor.show()
    sys.exit(app.exec_())
