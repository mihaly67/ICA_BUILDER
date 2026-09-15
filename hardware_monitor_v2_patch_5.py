with open('local_hardware_monitor_v2_new2.py', 'r') as f:
    code = f.read()

# Add Context Menu capabilities for Killing processes to QTableView
search_table_setup = """        self.table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.table_view.setStyleSheet(\"\"\"
            QTableView { background-color: #1e293b; color: white; gridline-color: #334155; border: none; }
            QHeaderView::section { background-color: #0f172a; color: #94a3b8; font-weight: bold; border: 1px solid #334155; }
        \"\"\")
        self.layout.addWidget(self.table_view)"""

replace_table_setup = """        self.table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.table_view.setStyleSheet(\"\"\"
            QTableView { background-color: #1e293b; color: white; gridline-color: #334155; border: none; }
            QHeaderView::section { background-color: #0f172a; color: #94a3b8; font-weight: bold; border: 1px solid #334155; }
        \"\"\")

        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_process_menu)

        self.layout.addWidget(self.table_view)"""

code = code.replace(search_table_setup, replace_table_setup)

search_functions = """    def get_uptime(self):"""

replace_functions = """    def show_process_menu(self, pos):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        # Retrieve the PID from the proxy model
        pid_index = self.proxy_model.index(row, 1)
        name_index = self.proxy_model.index(row, 0)

        pid = int(self.proxy_model.data(pid_index, Qt.DisplayRole))
        name = self.proxy_model.data(name_index, Qt.DisplayRole)

        menu = QMenu(self)
        kill_action = QAction(f"Kill Process ({name} - PID: {pid})", self)

        def kill_process():
            try:
                # Basic kill attempt
                p = psutil.Process(pid)
                p.kill()
                self.tray_icon.showMessage("Hardver Monitor", f"Folyamat bezárva: {name}", QSystemTrayIcon.Information, 2000)
            except psutil.AccessDenied:
                # If access is denied, use pkexec for sudo kill
                try:
                    subprocess.Popen(f"pkexec kill -9 {pid}", shell=True)
                except:
                    pass
            except Exception:
                pass

        kill_action.triggered.connect(kill_process)
        menu.addAction(kill_action)
        menu.exec_(self.table_view.viewport().mapToGlobal(pos))

    def get_uptime(self):"""

code = code.replace(search_functions, replace_functions)

with open('local_hardware_monitor_v2_new3.py', 'w') as f:
    f.write(code)
