import re

with open('src/hardware_monitor_v2.py', 'r') as f:
    content = f.read()

# Add detect_gpus definition
search = """    def get_uptime(self):"""
replace = """    def detect_gpus(self):
        try:
            import subprocess
            cmd = "nvidia-smi --query-gpu=index,name --format=csv,noheader"
            output = subprocess.check_output(cmd, shell=True, text=True).strip()
            if output:
                for line in output.split('\\n'):
                    parts = line.split(',')
                    if len(parts) >= 2:
                        idx = int(parts[0].strip())
                        name = parts[1].strip()
                        self.gpu_names[idx] = name

                        core_bar = ResourceBar(f"[{idx}] {name} (Mag)")
                        vram_bar = ResourceBar(f"[{idx}] {name} (VRAM)")
                        self.gpu_layout.addWidget(core_bar)
                        self.gpu_layout.addWidget(vram_bar)

                        self.gpu_bars[idx] = {'core': core_bar, 'vram': vram_bar, 'name': name}
        except Exception as e:
            fallback = ResourceBar("GPU (Nvidia-smi hiba)")
            self.gpu_layout.addWidget(fallback)

    def get_uptime(self):"""
content = content.replace(search, replace)
with open('src/hardware_monitor_v2.py', 'w') as f:
    f.write(content)
