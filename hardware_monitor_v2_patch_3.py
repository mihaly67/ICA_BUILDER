with open('local_hardware_monitor_v2_new.py', 'r') as f:
    code = f.read()

# Let's add power estimation or fallback
search_temp = """        self.sensor_header.setText(f"Hőmérséklet (CPU): {temp_str}  |  Teljesítmény: ~ N/A Watt (Készül)")"""

replace_temp = """        # Attempt to read CPU Power (Watts) if available via RAPL or fallback
        power_str = "N/A"
        if not hasattr(self, 'last_energy'):
            self.last_energy = 0
            self.last_energy_time = 0

        try:
            energy_files = ['/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj', '/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0/energy_uj']
            for e_file in energy_files:
                if os.path.exists(e_file):
                    energy = int(open(e_file).read().strip())
                    import time
                    now = time.time()
                    if self.last_energy > 0 and (now - self.last_energy_time) > 0:
                        delta_uj = energy - self.last_energy
                        delta_s = now - self.last_energy_time
                        power_w = (delta_uj / 1e6) / delta_s
                        power_str = f"{power_w:.1f} W"
                    self.last_energy = energy
                    self.last_energy_time = now
                    break
        except:
            pass

        self.sensor_header.setText(f"Hőmérséklet (CPU): {temp_str}  |  Teljesítmény: {power_str}")"""

code = code.replace(search_temp, replace_temp)

with open('local_hardware_monitor_v2_new.py', 'w') as f:
    f.write(code)
