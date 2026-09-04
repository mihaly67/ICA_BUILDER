import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QListWidget, QFrame)
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette

class ServiceController:
    @staticmethod
    def run_cmd(cmd):
        try:
            # We must use piped password to circumvent strict sysvinit background prompt requirements
            # without triggering interactive popups that stall.
            subprocess.Popen(f"echo '1104' | sudo -S {cmd}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            pass

    @staticmethod
    def get_status(check_cmd):
        try:
            res = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            return res.returncode == 0
        except:
            return False

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_statuses)
        self.timer.start(2000)

    def initUI(self):
        self.setWindowTitle("CyberSec Control Center")
        self.resize(700, 450)

        # Dark, modern "hacker" UI palette inspired by some modern repos
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QListWidget {
                background-color: #1e293b;
                color: #94a3b8;
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
            QListWidget::item { padding: 15px; border-radius: 8px; }
            QListWidget::item:selected { background-color: #334155; color: #f8fafc; }
            QListWidget::item:hover { background-color: #475569; color: #f8fafc; }

            QLabel { color: #f1f5f9; }

            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1d4ed8; }
            QPushButton#stopBtn { background-color: #ef4444; }
            QPushButton#stopBtn:hover { background-color: #dc2626; }
            QPushButton#stopBtn:pressed { background-color: #b91c1c; }

            QFrame#mainPanel {
                background-color: #1e293b;
                border-radius: 12px;
            }
            QFrame#statusCard {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)

        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem("🛡️ ClamAV")
        self.sidebar.addItem("🧱 Fail2ban")
        self.sidebar.addItem("👁️ Watchdog")
        self.sidebar.currentRowChanged.connect(self.switch_page)

        # Main Content Area
        self.stack = QStackedWidget()

        # Pages
        self.clam_page, self.clam_status = self.create_page(
            "ClamAV Antivirus Daemon",
            "Protects the system against malicious files and trojans.",
            lambda: ServiceController.run_cmd("service clamav-daemon start"),
            lambda: ServiceController.run_cmd("service clamav-daemon stop")
        )
        self.f2b_page, self.f2b_status = self.create_page(
            "Fail2ban Intrusion Prevention",
            "Bans IPs that show malicious signs like too many password failures.",
            lambda: ServiceController.run_cmd("service fail2ban start"),
            lambda: ServiceController.run_cmd("service fail2ban stop")
        )
        self.wd_page, self.wd_status = self.create_page(
            "Merkava Cryptominer Watchdog",
            "Continuously scans process list and kills known crypto miners.",
            lambda: ServiceController.run_cmd("bash -c '(sudo crontab -l 2>/dev/null | grep -v miner_watchdog; echo \"* * * * * /usr/local/bin/miner_watchdog.sh\") | sudo crontab -'"),
            lambda: ServiceController.run_cmd("bash -c 'sudo crontab -l 2>/dev/null | grep -v miner_watchdog | sudo crontab -'")
        )

        self.stack.addWidget(self.clam_page)
        self.stack.addWidget(self.f2b_page)
        self.stack.addWidget(self.wd_page)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.sidebar.setCurrentRow(0)
        self.update_statuses()

    def create_page(self, title_text, desc_text, start_cb, stop_cb):
        page = QFrame()
        page.setObjectName("mainPanel")
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))

        # Description
        desc = QLabel(desc_text)
        desc.setFont(QFont("Segoe UI", 12))
        desc.setStyleSheet("color: #94a3b8;")
        desc.setWordWrap(True)

        # Status Card
        status_card = QFrame()
        status_card.setObjectName("statusCard")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(20, 20, 20, 20)

        status_header = QLabel("CURRENT STATUS")
        status_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        status_header.setStyleSheet("color: #64748b;")

        status_lbl = QLabel("Checking...")
        status_lbl.setFont(QFont("Consolas", 18, QFont.Bold))

        status_layout.addWidget(status_header)
        status_layout.addWidget(status_lbl)
        status_card.setLayout(status_layout)

        # Controls
        controls_layout = QHBoxLayout()
        btn_start = QPushButton("START SERVICE")
        btn_start.setCursor(Qt.PointingHandCursor)
        btn_start.clicked.connect(start_cb)
        btn_start.clicked.connect(lambda: QTimer.singleShot(1000, self.update_statuses))

        btn_stop = QPushButton("STOP SERVICE")
        btn_stop.setObjectName("stopBtn")
        btn_stop.setCursor(Qt.PointingHandCursor)
        btn_stop.clicked.connect(stop_cb)
        btn_stop.clicked.connect(lambda: QTimer.singleShot(1000, self.update_statuses))

        controls_layout.addWidget(btn_start)
        controls_layout.addWidget(btn_stop)

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addSpacing(20)
        layout.addWidget(status_card)
        layout.addStretch()
        layout.addLayout(controls_layout)

        page.setLayout(layout)
        return page, status_lbl

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)

    def update_statuses(self):
        # ClamAV
        if ServiceController.get_status("pgrep -f clamd"):
            self.clam_status.setText("● SYSTEM ACTIVE")
            self.clam_status.setStyleSheet("color: #22c55e;") # Tailwind Green
        else:
            self.clam_status.setText("○ SYSTEM OFFLINE")
            self.clam_status.setStyleSheet("color: #64748b;") # Tailwind Slate

        # Fail2ban
        if ServiceController.get_status("pgrep -f fail2ban-server"):
            self.f2b_status.setText("● SYSTEM ACTIVE")
            self.f2b_status.setStyleSheet("color: #22c55e;")
        else:
            self.f2b_status.setText("○ SYSTEM OFFLINE")
            self.f2b_status.setStyleSheet("color: #64748b;")

        # Watchdog
        if ServiceController.get_status("echo '1104' | sudo -S crontab -l 2>/dev/null | grep -q miner_watchdog"):
            self.wd_status.setText("● SYSTEM ACTIVE")
            self.wd_status.setStyleSheet("color: #22c55e;")
        else:
            self.wd_status.setText("○ SYSTEM OFFLINE")
            self.wd_status.setStyleSheet("color: #64748b;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())
