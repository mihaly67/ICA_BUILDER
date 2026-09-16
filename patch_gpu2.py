import re

with open('src/hardware_monitor_v2.py', 'r') as f:
    content = f.read()

# Make sure detect_gpus is called in __init__
search1 = """        # --- GPU Szekció ---
        gpu_header = QLabel("GPU & VRAM (NVIDIA)")
        gpu_header.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.layout.addWidget(gpu_header)

        self.gpu_bar = ResourceBar("GPU Mag")
        self.vram_bar = ResourceBar("VRAM")
        self.layout.addWidget(self.gpu_bar)
        self.layout.addWidget(self.vram_bar)"""

replace1 = """        # --- GPU Szekció ---
        gpu_header = QLabel("Dinamikus Dual-GPU & VRAM (NVIDIA)")
        gpu_header.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.layout.addWidget(gpu_header)

        self.gpu_layout = QVBoxLayout()
        self.layout.addLayout(self.gpu_layout)
        self.gpu_bars = {} # { gpu_index: {'core': bar, 'vram': bar, 'name': str} }
        self.gpu_names = {}

        # Kezdeti GPU-k detektálása (nvidia-smi-vel)
        self.detect_gpus()"""

content = content.replace(search1, replace1)

# Modify update_stats for GPU
search2 = """        # 2. GPU Frissítés
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
            self.gpu_bar.label_text = "GPU (Nem elérhető)" """

replace2 = """        # 2. GPU Frissítés
        try:
            # Get multiple GPU stats: index, utilization.gpu, utilization.memory, memory.used, memory.total
            cmd = "nvidia-smi --query-gpu=index,utilization.gpu,utilization.memory,memory.used,memory.total --format=csv,noheader,nounits"
            output = subprocess.check_output(cmd, shell=True, text=True).strip()
            if output:
                for line in output.split('\\n'):
                    parts = line.split(',')
                    if len(parts) >= 5:
                        idx = int(parts[0].strip())
                        gpu_util = float(parts[1].strip())
                        mem_util = float(parts[2].strip())
                        mem_used = int(parts[3].strip())
                        mem_total = int(parts[4].strip())

                        if idx in self.gpu_bars:
                            bar_dict = self.gpu_bars[idx]

                            # Add compute status text if under load
                            c_state = "Aktív (CUDA Compute)" if gpu_util > 5 or mem_util > 5 else "Tétlen"

                            bar_dict['core'].update_values(gpu_util)
                            bar_dict['core'].label_text = f"[{idx}] {bar_dict['name']} (Mag) | {c_state}"

                            bar_dict['vram'].update_values(mem_util)
                            bar_dict['vram'].label_text = f"[{idx}] {bar_dict['name']} (VRAM) | {mem_used}MB / {mem_total}MB"

        except Exception:
            pass # Use default UI if failed """

content = content.replace(search2, replace2)

# Make sure total_cpu_bar text includes freq
search3 = """        else:
            self.total_cpu_bar.update_values(total_times.user, total_times.system)

        for i, c in enumerate(core_times):"""
replace3 = """        else:
            self.total_cpu_bar.update_values(total_times.user, total_times.system)

        # Total frekvencia kiírása
        total_freq_text = ""
        # Calculate average of all cores' Avg_MHz
        if freqs:
            avg_all_mhz = sum(freqs.values()) / len(freqs)
            total_freq_text = f" {int(avg_all_mhz)}MHz"
        self.total_cpu_bar.label_text = f"CPU Összesített{total_freq_text}"

        for i, c in enumerate(core_times):"""

content = content.replace(search3, replace3)

with open('src/hardware_monitor_v2.py', 'w') as f:
    f.write(content)
