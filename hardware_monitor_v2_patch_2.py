with open('local_hardware_monitor_v2_new.py', 'r') as f:
    code = f.read()

# Replace the layout replacement code again to make it purely dynamic based on core count instead of fixed boundaries
search_cpu_layout = """        from PyQt5.QtWidgets import QGridLayout
        cpu_layout = QGridLayout()
        # Determine number of columns dynamically (e.g. 2, 4, 8)
        if self.cpu_count <= 8:
            cols = 2
        elif self.cpu_count <= 20:
            cols = 4
        else:
            cols = 8

        for i in range(self.cpu_count):
            # C-State based color support will change this label later dynamically
            bar = ResourceBar(f"CPU {i}")
            self.cpu_bars.append(bar)
            row = i // cols
            col = i % cols
            cpu_layout.addWidget(bar, row, col)

        self.layout.addLayout(cpu_layout)"""

replace_cpu_layout = """        from PyQt5.QtWidgets import QGridLayout
        cpu_layout = QGridLayout()

        # Calculate dynamic columns: max 5 rows, then expand columns
        cols = max(2, (self.cpu_count + 4) // 5)

        for i in range(self.cpu_count):
            bar = ResourceBar(f"CPU {i}")
            self.cpu_bars.append(bar)
            row = i // cols
            col = i % cols
            cpu_layout.addWidget(bar, row, col)

        self.layout.addLayout(cpu_layout)"""

code = code.replace(search_cpu_layout, replace_cpu_layout)

with open('local_hardware_monitor_v2_new.py', 'w') as f:
    f.write(code)
