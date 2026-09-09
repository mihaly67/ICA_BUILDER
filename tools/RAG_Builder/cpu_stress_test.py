import sys
import os
import shutil
import psutil
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QSpinBox, QComboBox, QSizePolicy, QTextEdit)
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QFont, QPalette, QColor

class CpuStressTestApp(QWidget):
    def __init__(self):
        super().__init__()

        try:
            self.max_cores = os.cpu_count() or 4
        except:
            self.max_cores = 4

        try:
            total_ram_mb = psutil.virtual_memory().total // (1024 * 1024)
            self.target_ram = int(total_ram_mb * 0.75)
        except:
            self.target_ram = 4000

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.initUI()

    def initUI(self):
        self.setWindowTitle('MX CPU Stress Tester')
        self.setMinimumSize(750, 550)

        # --- KDE Plasma / Breeze Dark stílus beállítása ---
        self.setStyleSheet("""
            QWidget {
                background-color: #31363b;
                color: #eff0f1;
                font-family: 'Noto Sans', sans-serif;
            }
            QPushButton {
                background-color: #3daee9;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4ebff9;
            }
            QPushButton:pressed {
                background-color: #2b82b0;
            }
            QPushButton:disabled {
                background-color: #4d5257;
                color: #8c9298;
            }
            QSpinBox, QComboBox {
                background-color: #232629;
                border: 1px solid #76797c;
                padding: 6px;
                border-radius: 4px;
                color: #eff0f1;
                selection-background-color: #3daee9;
            }
            QComboBox::drop-down {
                border-left: 1px solid #76797c;
            }
            QTextEdit {
                background-color: #232629;
                border: 1px solid #76797c;
                border-radius: 4px;
                font-family: 'Hack', 'Monospace', monospace;
                font-size: 11px;
                color: #27ae60;
                padding: 5px;
            }
            QLabel {
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("MX CPU STRESS TESTER")
        title.setFont(QFont('Noto Sans', 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #3daee9;")
        title.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        layout.addWidget(title)

        desc = QLabel("Hardware instability and thermal throttling diagnostic tool.\n"
                      "Select a Torture Test mode and click Start to verify system stability under heavy load.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #a5a9ad; font-size: 12px;")
        desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(desc)

        # --- Beállítások rész ---
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(10)

        lbl_threads = QLabel("Threads / Cores:")
        self.spin_threads = QSpinBox()
        self.spin_threads.setMinimum(1)
        self.spin_threads.setMaximum(self.max_cores)
        self.spin_threads.setValue(self.max_cores)
        self.spin_threads.setFixedWidth(80)

        settings_layout.addWidget(lbl_threads)
        settings_layout.addWidget(self.spin_threads)

        lbl_mode = QLabel(" Test Mode:")
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("1. Smallest FFTs (L1/L2 Cache, Max Heat)", 1)
        self.combo_mode.addItem("2. Small FFTs (L1/L2/L3 Cache, Max Power)", 2)
        self.combo_mode.addItem("3. Large FFTs (Memory Controller & RAM)", 3)
        self.combo_mode.addItem("4. Blend (Tests CPU & RAM combined)", 4)
        self.combo_mode.setCurrentIndex(3)
        self.combo_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        settings_layout.addWidget(lbl_mode)
        settings_layout.addWidget(self.combo_mode)

        layout.addLayout(settings_layout)

        # --- Napló ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # --- Állapot ---
        self.lbl_status = QLabel("Status: READY")
        self.lbl_status.setFont(QFont('Noto Sans', 14, QFont.Bold))
        self.lbl_status.setStyleSheet("color: #27ae60;")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status)

        # --- Gombok ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        self.btn_start = QPushButton("START TEST")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_stress)

        self.btn_stop = QPushButton("STOP TEST")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setStyleSheet("background-color: #da4453;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_stress)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def start_stress(self):
        num_threads = self.spin_threads.value()
        mode_id = self.combo_mode.currentData()

        self.stop_stress()
        self.log_output.clear()
        self.log_message(f"--- Initializing MPrime Torture Test ---")

        workdir = "/tmp/mprime_stress"
        os.makedirs(workdir, exist_ok=True)

        local_txt = os.path.join(workdir, "local.txt")
        prime_txt = os.path.join(workdir, "prime.txt")

        with open(local_txt, "w") as f:
            f.write(f"WorkerThreads={num_threads}\n")

        min_fft = 4
        max_fft = 8192
        mem = 0

        if mode_id == 1:
            min_fft, max_fft, mem = 4, 86, 0
        elif mode_id == 2:
            min_fft, max_fft, mem = 148, 200, 0
        elif mode_id == 3:
            min_fft, max_fft, mem = 343, 8192, self.target_ram
        elif mode_id == 4:
            min_fft, max_fft, mem = 4, 8192, self.target_ram

        with open(prime_txt, "w") as f:
            f.write("V24OptionsConverted=1\n")
            f.write("V30OptionsConverted=1\n")
            f.write("StressTester=1\n")
            f.write(f"MinTortureFFT={min_fft}\n")
            f.write(f"MaxTortureFFT={max_fft}\n")
            f.write(f"TortureMem={mem}\n")
            f.write("TortureTime=3\n")
            f.write("TortureWeak=0\n")
            f.write("[PrimeNet]\nDebug=0\n")

        self.log_message(f"Configuration: {num_threads} threads, Mode: {mode_id}, RAM Allocated: {mem} MB")
        self.log_message("Spawning mprime process...")

        self.process.setWorkingDirectory(workdir)
        self.process.start("mprime", ["-t", "-w" + workdir])

        self.lbl_status.setText("Status: TESTING IN PROGRESS")
        self.lbl_status.setStyleSheet("color: #f67400;") # KDE Orange

        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet("background-color: #4d5257;")
        self.spin_threads.setEnabled(False)
        self.combo_mode.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_stop.setStyleSheet("background-color: #da4453;") # Red stop button enabled

    def stop_stress(self):
        if self.process.state() == QProcess.Running:
            self.process.terminate()
            self.process.waitForFinished(1000)
            if self.process.state() == QProcess.Running:
                self.process.kill()

        subprocess.run(["killall", "-9", "mprime"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.lbl_status.setText("Status: READY")
        self.lbl_status.setStyleSheet("color: #27ae60;") # KDE Green

        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet("background-color: #3daee9;")
        self.spin_threads.setEnabled(True)
        self.combo_mode.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #4d5257;")

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf8", errors="ignore").strip()
        if text:
            lines = text.split('\n')
            for line in lines:
                self.log_message(line)

            if "error" in text.lower() or "hardware failure" in text.lower():
                self.lbl_status.setText("Status: HARDWARE FAILURE DETECTED")
                self.lbl_status.setStyleSheet("color: #da4453;")
                self.log_output.append(f"<span style='color:#da4453;'><b>{text}</b></span>")

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode("utf8", errors="ignore").strip()
        if text:
            self.log_output.append(f"<span style='color:#da4453;'>{text}</span>")

    def process_finished(self, exitCode, exitStatus):
        if exitStatus == QProcess.CrashExit:
            self.log_message("Error: mprime crashed unexpectedly.")
        else:
            self.log_message("Test sequence completed.")
        self.stop_stress()

    def log_message(self, message):
        self.log_output.append(message)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        self.stop_stress()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CpuStressTestApp()
    ex.show()
    sys.exit(app.exec_())
