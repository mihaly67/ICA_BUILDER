import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# 1. Beágyazzuk a Chart.js-t a D3.js mellé
html_head = '''    <script src="https://d3js.org/d3.v7.min.js"></script>'''
new_html_head = '''    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'''
content = content.replace(html_head, new_html_head)

# 2. Hozzáadjuk a System Health, Swarm Inbox és Chart vizualizációkat a HTML-hez
old_telemetry = '''        <!-- Telemetria Panel -->'''
new_telemetry = '''        <!-- System Health & Inbox (ÚJ) -->
        <div class="col-lg-12 mb-4">
            <div class="row">
                <div class="col-md-6">
                    <div class="card shadow-sm border-success">
                        <div class="card-header bg-success text-dark">💻 Rendszer Állapot (System Health)</div>
                        <div class="card-body bg-dark">
                            <pre id="system-health-data" class="m-0 text-success" style="font-size: 12px; height: 100px; overflow-y: auto;">Betöltés...</pre>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card shadow-sm border-danger">
                        <div class="card-header bg-danger text-white">📥 Swarm INBOX (Üzenetek / Feladatok)</div>
                        <div class="card-body bg-dark">
                            <pre id="swarm-inbox-data" class="m-0 text-danger" style="font-size: 12px; height: 100px; overflow-y: auto;">Betöltés...</pre>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row mt-2">
                <div class="col-12">
                     <div class="card shadow-sm border-secondary">
                        <div class="card-header bg-secondary text-white">📈 MCP Hívások Futási Ideje (ms)</div>
                        <div class="card-body bg-dark" style="height: 250px;">
                            <canvas id="telemetryChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Telemetria Panel -->'''
content = content.replace(old_telemetry, new_telemetry)

# 3. Kliens oldali JS frissítése a Chart.js és az új adatok kezelésére
old_update_js = '''                // Telemetria statisztikák'''
new_update_js = '''                // Rendszer állapot
                document.getElementById('system-health-data').innerText = data.system_health || "Nincs adat";

                // Swarm Inbox
                document.getElementById('swarm-inbox-data').innerText = data.swarm_inbox || "Üres / Nincs aktív feladat";

                // Telemetria Chart.js frissítése
                updateTelemetryChart(data.telemetry);

                // Telemetria statisztikák'''
content = content.replace(old_update_js, new_update_js)

old_chart_init = '''    let currentMctsDataStr = "";'''
new_chart_init = '''    let telemetryChartInstance = null;

    function updateTelemetryChart(telemetryData) {
        const ctx = document.getElementById('telemetryChart').getContext('2d');

        // Vesszük az utolsó 20-at és megfordítjuk az időrendhez
        const chartData = [...telemetryData].reverse();
        const labels = chartData.map(d => d.time.split(' ')[1]); // Csak az idő
        const durations = chartData.map(d => d.duration);
        const bgColors = chartData.map(d => d.status === 'success' ? 'rgba(74, 222, 128, 0.6)' : 'rgba(248, 113, 113, 0.6)');

        if (telemetryChartInstance) {
            telemetryChartInstance.data.labels = labels;
            telemetryChartInstance.data.datasets[0].data = durations;
            telemetryChartInstance.data.datasets[0].backgroundColor = bgColors;
            telemetryChartInstance.update();
        } else {
            telemetryChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Futási idő (ms)',
                        data: durations,
                        backgroundColor: bgColors,
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#aaa' } },
                        x: { grid: { color: '#333' }, ticks: { color: '#aaa', maxRotation: 45, minRotation: 45 } }
                    },
                    plugins: {
                        legend: { labels: { color: '#fff' } }
                    }
                }
            });
        }
    }

    let currentMctsDataStr = "";'''
content = content.replace(old_chart_init, new_chart_init)

# 4. Backend (Python API) kiegészítése a Health és az Inbox adatok beolvasásával
old_api_return = '''    # 4. Tudásgráf lekérése'''
new_api_return = '''    # Extra adatok (Health, Inbox)
    system_health_str = "Nem elérhető"
    try:
        import subprocess
        cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1\"%\"}'", shell=True).decode().strip()
        mem = subprocess.check_output("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'", shell=True).decode().strip()
        disk = subprocess.check_output("df -h / | awk '$NF==\"/\"{printf \"%s\", $5}'", shell=True).decode().strip()
        system_health_str = f"CPU Használat: {cpu}\\nRAM Használat: {mem}\\nLemez (/): {disk}"
    except Exception as e:
        system_health_str = f"Hiba: {e}"

    inbox_str = ""
    inbox_dir = "/home/misi/Jules_mx/temp/inbox"
    try:
        if os.path.exists(inbox_dir):
            files = [f for f in os.listdir(inbox_dir) if f.startswith("msg_") and f.endswith(".txt")]
            if files:
                for f in files:
                    filepath = os.path.join(inbox_dir, f)
                    with open(filepath, 'r') as file:
                        inbox_str += f"[{f}]: {file.read()[:50]}...\\n"
            else:
                inbox_str = "Nincsenek várakozó Swarm üzenetek."
        else:
            inbox_str = "Inbox könyvtár nem létezik."
    except Exception as e:
        inbox_str = f"Hiba az Inbox olvasásakor: {e}"

    # 4. Tudásgráf lekérése'''
content = content.replace(old_api_return, new_api_return)

old_api_dict = '''        "mcts_latest": mcts_latest if 'mcts_latest' in locals() else {},'''
new_api_dict = '''        "system_health": system_health_str if 'system_health_str' in locals() else "",
        "swarm_inbox": inbox_str if 'inbox_str' in locals() else "",
        "mcts_latest": mcts_latest if 'mcts_latest' in locals() else {},'''
content = content.replace(old_api_dict, new_api_dict)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
