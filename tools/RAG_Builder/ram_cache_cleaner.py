import sys
import psutil
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class RamCacheCleanerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Frissítés másodpercenként
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def initUI(self):
        self.setWindowTitle('MX RAM & Cache Monitor')
        self.setMinimumSize(450, 300)

        # KDE Plasma / Breeze Dark Stílus
        self.setStyleSheet("""
            QWidget {
                background-color: #31363b;
                color: #eff0f1;
                font-family: 'Noto Sans', sans-serif;
            }
            QPushButton {
                background-color: #da4453;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ed5362;
            }
            QPushButton:pressed {
                background-color: #c93543;
            }
            QProgressBar {
                border: 1px solid #76797c;
                border-radius: 4px;
                text-align: center;
                background-color: #232629;
                font-weight: bold;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #3daee9;
                border-radius: 3px;
            }
            #cacheBar::chunk {
                background-color: #f67400; /* Narancs a cache-nek */
            }
            #swapBar::chunk {
                background-color: #27ae60; /* Zöld a swap-nek */
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("MX RAM & CACHE CLEANER")
        title.setFont(QFont('Noto Sans', 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("Valós idejű memória és I/O Cache figyelő.")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # --- RAM ProgressBar ---
        layout.addWidget(QLabel("Aktív RAM Használat (Applikációk):"))
        self.ram_bar = QProgressBar()
        layout.addWidget(self.ram_bar)

        # --- Cache ProgressBar ---
        layout.addWidget(QLabel("Rendszer Buffers / Cache (Fájl gyorsítótár):"))
        self.cache_bar = QProgressBar()
        self.cache_bar.setObjectName("cacheBar")
        layout.addWidget(self.cache_bar)

        # --- Swap ProgressBar ---
        layout.addWidget(QLabel("Swap (Virtuális Memória):"))
        self.swap_bar = QProgressBar()
        self.swap_bar.setObjectName("swapBar")
        layout.addWidget(self.swap_bar)

        self.lbl_details = QLabel("Számítás folyamatban...")
        self.lbl_details.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_details)

        # --- Gomb ---
        btn_layout = QHBoxLayout()
        self.btn_clean = QPushButton("🗑️ CACHE ÉS RAM ÜRÍTÉSE")
        self.btn_clean.setCursor(Qt.PointingHandCursor)
        self.btn_clean.clicked.connect(self.clean_cache)
        btn_layout.addWidget(self.btn_clean)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.update_stats()

    def update_stats(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Memória számítások (MB-ban a szebb kijelzésért)
        total_mb = mem.total / (1024*1024)
        # Az "active" memória nagyjából az, amit a programok esznek
        # A Linuxban a buff/cache a mem.buffers + mem.cached
        cache_mb = (getattr(mem, 'buffers', 0) + getattr(mem, 'cached', 0)) / (1024*1024)
        # Tényleges program használat (Total - Free - Buff/Cache)
        used_mb = (mem.total - mem.available) / (1024*1024)

        ram_percent = int((used_mb / total_mb) * 100)
        cache_percent = int((cache_mb / total_mb) * 100)

        self.ram_bar.setValue(min(ram_percent, 100))
        self.ram_bar.setFormat(f"{int(used_mb)} MB / {int(total_mb)} MB ({ram_percent}%)")

        self.cache_bar.setValue(min(cache_percent, 100))
        self.cache_bar.setFormat(f"{int(cache_mb)} MB Szemetelődés ({cache_percent}%)")

        self.swap_bar.setValue(int(swap.percent))
        self.swap_bar.setFormat(f"{int(swap.used / (1024*1024))} MB / {int(swap.total / (1024*1024))} MB ({swap.percent}%)")

    def clean_cache(self):
        self.btn_clean.setText("⏳ Ürítés folyamatban...")
        self.btn_clean.setEnabled(False)
        QApplication.processEvents()

        try:
            # Drop caches parancs pkexec segítségével (grafikus jelszókérés, ha kell)
            # A sync garantálja, hogy a lemezre írás megtörténjen a törlés előtt
            cmd = "pkexec sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'"
            subprocess.run(cmd, shell=True)
        except Exception as e:
            print(f"Hiba az ürítés során: {e}")

        self.btn_clean.setText("🗑️ CACHE ÉS RAM ÜRÍTÉSE")
        self.btn_clean.setEnabled(True)
        self.update_stats()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RamCacheCleanerApp()
    ex.show()
    sys.exit(app.exec_())
