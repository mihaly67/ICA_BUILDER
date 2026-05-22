from flask import Flask, jsonify, render_template_string
import sqlite3
import json
import os
import time

app = Flask(__name__)

DB_PATH = "/home/misi/Jules_ICA_Builder/mcp_telemetry.db"
MEMORY_PATH = "/home/misi/Jules_ICA_Builder/agent_memory.jsonl"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="hu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jules ICA - Rendszerfelügyelet</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: monospace; }
        .card { background-color: #1e1e1e; border: 1px solid #333; margin-bottom: 20px; }
        .card-header { background-color: #2c2c2c; border-bottom: 1px solid #444; font-weight: bold; }
        .table { color: #e0e0e0; }
        .table-striped tbody tr:nth-of-type(odd) { background-color: #2a2a2a; }
        .table-dark th { background-color: #333; }
        .status-ok { color: #4ade80; font-weight: bold; }
        .status-err { color: #f87171; font-weight: bold; }
        .memory-box { max-height: 400px; overflow-y: auto; background: #000; padding: 15px; border-radius: 5px; }
        .log-entry { margin-bottom: 10px; border-bottom: 1px dashed #333; padding-bottom: 5px; }
        .log-time { color: #60a5fa; }
        .log-cat { color: #c084fc; font-weight: bold; }
    </style>
</head>
<body>
<div class="container-fluid py-4">
    <h2 class="mb-4 text-center text-primary">🧠 Jules ICA System Monitor</h2>

    <div class="row">
        <!-- Telemetria Panel -->
        <div class="col-lg-8">
            <div class="card shadow-sm">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>⚙️ MCP Telemetria & Tool Hívások</span>
                    <span id="telemetry-stats" class="badge bg-secondary">Betöltés...</span>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive" style="max-height: 500px;">
                        <table class="table table-dark table-striped table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Időpont</th>
                                    <th>Eszköz (Tool)</th>
                                    <th>Idő (ms)</th>
                                    <th>Státusz</th>
                                    <th>Részletek / Hiba</th>
                                </tr>
                            </thead>
                            <tbody id="telemetry-body">
                                <!-- JS tölti ki -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Memória Panel -->
        <div class="col-lg-4">
            <div class="card shadow-sm">
                <div class="card-header">
                    📖 Agent Memory Stream
                </div>
                <div class="card-body memory-box" id="memory-body">
                    <!-- JS tölti ki -->
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    function updateDashboard() {
        fetch('/api/data')
            .then(response => response.json())
            .then(data => {
                // Telemetria statisztikák
                document.getElementById('telemetry-stats').innerText =
                    `Összes: ${data.stats.total} | Átlag: ${data.stats.avg_time.toFixed(1)}ms | Hiba: ${data.stats.error_rate.toFixed(1)}%`;

                // Telemetria tábla
                const tbody = document.getElementById('telemetry-body');
                tbody.innerHTML = '';
                data.telemetry.forEach(row => {
                    const statusClass = row.status === 'success' ? 'status-ok' : 'status-err';
                    const statusText = row.status === 'success' ? 'OK' : 'ERR';
                    let toolName = row.tool_name;
                    let args = row.args_raw;

                    try {
                        const argsObj = JSON.parse(row.args_raw);
                        if (toolName === "execute_bash") {
                            toolName = `<span class="text-info">bash:</span> ${argsObj.command ? argsObj.command.substring(0,40) + '...' : ''}`;
                            args = '';
                        } else if (toolName === "write_file_mcp") {
                            const fp = argsObj.filepath ? argsObj.filepath.split('/').pop() : '';
                            toolName = `<span class="text-warning">write:</span> ${fp}`;
                            args = '';
                        }
                    } catch(e) {}

                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${row.time}</td>
                        <td>${toolName}</td>
                        <td class="text-end text-success">${row.duration.toFixed(1)}</td>
                        <td class="${statusClass} text-center">${statusText}</td>
                        <td><small class="text-muted">${row.error || args.substring(0, 50)}</small></td>
                    `;
                    tbody.appendChild(tr);
                });

                // Memória stream
                const memBody = document.getElementById('memory-body');
                memBody.innerHTML = '';
                data.memory.forEach(mem => {
                    const ts = mem.timestamp ? mem.timestamp.split('T')[0] : '';
                    const content = mem.content ? mem.content.substring(0, 150) + '...' : '';
                    memBody.innerHTML += `
                        <div class="log-entry">
                            <span class="log-time">[${ts}]</span>
                            <span class="log-cat">${mem.category || 'Event'}</span><br>
                            <span class="text-light">${content}</span>
                        </div>
                    `;
                });
            })
            .catch(err => console.error("Hiba az adatok lekérésekor:", err));
    }

    // Frissítés másodpercenként
    setInterval(updateDashboard, 1000);
    updateDashboard();
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    # 1. Statisztikák lekérése
    stats = {"total": 0, "avg_time": 0, "error_rate": 0}
    telemetry_rows = []
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*), AVG(execution_time_ms) FROM mcp_logs")
            total, avg_time = c.fetchone()
            c.execute("SELECT COUNT(*) FROM mcp_logs WHERE status='error'")
            errors = c.fetchone()[0]

            if total:
                stats = {
                    "total": total,
                    "avg_time": avg_time if avg_time else 0,
                    "error_rate": (errors / total * 100) if total > 0 else 0
                }

            # 2. Utolsó 20 hívás lekérése
            c.execute("SELECT timestamp, tool_name, args, execution_time_ms, status, error_msg FROM mcp_logs ORDER BY id DESC LIMIT 20")
            for r in c.fetchall():
                ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r[0]))
                telemetry_rows.append({
                    "time": ts_str,
                    "tool_name": r[1],
                    "args_raw": r[2],
                    "duration": r[3],
                    "status": r[4],
                    "error": r[5] if r[5] else ""
                })
            conn.close()
        except Exception as e:
            print("DB hiba:", e)

    # 3. JSONL memória lekérése
    memory_entries = []
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines[-15:]):  # Utolsó 15 bejegyzés, legújabb elöl
                    try:
                        memory_entries.append(json.loads(line))
                    except:
                        pass
        except Exception as e:
            print("Memory hiba:", e)

    return jsonify({
        "stats": stats,
        "telemetry": telemetry_rows,
        "memory": memory_entries
    })

if __name__ == '__main__':
    # 8080-as porton indítjuk el, hogy a VPS-ről elérhető legyen
    app.run(host='0.0.0.0', port=8080)
