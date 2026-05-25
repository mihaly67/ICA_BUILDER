from flask import Flask, jsonify, render_template_string
import sqlite3
import json
import os
import time
import uuid
import logging
import html
import psutil
import shutil

# Globális logging inicializálás az információ-szivárgás elkerülésére
# psutil CPU percent initial call to calibrate interval=None later
psutil.cpu_percent()

if not logging.getLogger().handlers:
    logging.basicConfig(filename='monitor_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache a CPU használathoz, hogy a gyors API hívások ne mutassanak 0.0%-ot
last_cpu_time = 0
last_cpu_percent = 0.0

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
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        <!-- Kognitív Pipeline & System Állapot (ÚJ) -->
        <div class="col-lg-12 mb-4">
            <div class="card shadow-sm border-primary">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                    <span>🧠 Kognitív Pipeline (Önreflexió, Guardrails, Blueprint)</span>
                    <span id="cog-status" class="badge bg-dark">Aktív</span>
                </div>
                <div class="card-body bg-dark text-light p-3">
                    <div class="row">
                        <div class="col-md-3">
                            <h6 class="text-info border-bottom border-secondary pb-1">🛡️ Pipeline Gate (Guardrails)</h6>
                            <div id="guardrails-status" style="font-size: 13px;">Betöltés...</div>
                        </div>
                        <div class="col-md-3">
                            <h6 class="text-warning border-bottom border-secondary pb-1">📜 Blueprint Állapot</h6>
                            <div id="blueprint-status" style="font-size: 13px;">Betöltés...</div>
                        </div>
                        <div class="col-md-6">
                            <h6 class="text-danger border-bottom border-secondary pb-1">👿 Ördög Ügyvédje / Önreflexió (Legutóbbi)</h6>
                            <div id="reflection-status" style="font-size: 13px; max-height: 80px; overflow-y: auto;">Betöltés...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Health & Inbox (ÚJ) -->
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

        <!-- Telemetria Panel -->
        <div class="col-lg-8">
            <div class="card shadow-sm">
                <div class="card-header d-flex justify-content-between align-items-center text-white">
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

        <!-- MCTS Vizualizáció Panel -->
        <div class="col-lg-12 mt-4">
            <div class="card shadow-sm border-info">
                <div class="card-header bg-info text-dark d-flex justify-content-between align-items-center">
                    <span>🌳 MCTS Mély Tervezés (System 2 Gondolatfa)</span>
                    <span id="mcts-status" class="badge bg-dark">Várakozás adatra...</span>
                </div>
                <div class="card-body" style="background-color: #0d1117; position: relative;">
                    <div id="mcts-graph" style="width: 100%; height: 500px; overflow: hidden;"></div>
                </div>
            </div>
        </div>

        <!-- Tudásgráf Vizualizáció Panel -->
        <div class="col-lg-12 mt-4">
            <div class="card shadow-sm border-warning">
                <div class="card-header bg-warning text-dark d-flex justify-content-between align-items-center">
                    <span>🕸️ ICA Tudásgráf (Knowledge Graph)</span>
                    <span id="graph-stats" class="badge bg-dark">Betöltés...</span>
                </div>
                <div class="card-body" style="background-color: #0d1117; position: relative;">
                    <div id="kg-graph" style="width: 100%; height: 600px; overflow: hidden;"></div>
                </div>
            </div>
        </div>

        <!-- Memória Panel -->
        <div class="col-lg-4">
            <div class="card shadow-sm">
                <div class="card-header d-flex justify-content-between align-items-center text-white">
                    <span>📖 Agent Memory Stream</span>
                    <span id="memory-stats" class="badge bg-primary">Méret: ...</span>
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
                // Kognitív Pipeline adatok
                document.getElementById('guardrails-status').innerHTML = data.guardrails_html || "Nincs adat";
                document.getElementById('blueprint-status').innerHTML = data.blueprint_html || "Nincs adat";
                document.getElementById('reflection-status').innerHTML = data.reflection_html || "Nincsenek aktív önreflexió bejegyzések.";

                // Rendszer állapot
                document.getElementById('system-health-data').innerText = data.system_health || "Nincs adat";

                // Swarm Inbox
                document.getElementById('swarm-inbox-data').innerText = data.swarm_inbox || "Üres / Nincs aktív feladat";

                // Telemetria Chart.js frissítése
                updateTelemetryChart(data.telemetry);

                // Telemetria statisztikák
                document.getElementById('telemetry-stats').innerText =
                    `Összes: ${data.stats.total} | Átlag: ${data.stats.avg_time.toFixed(1)}ms | Hiba: ${data.stats.error_rate.toFixed(1)}%`;

                // MCTS fa renderelés ha van adat
                const latestMctsData = data.mcts_latest;
                if (latestMctsData && Object.keys(latestMctsData).length > 0) {
                    document.getElementById('mcts-status').innerText = "Utolsó tervezés megjelenítve";
                    renderMCTSTree(latestMctsData);
                }

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
                        <td><small class="text-light">${row.error || args.substring(0, 70)}</small></td>
                    `;
                    tbody.appendChild(tr);
                });

                // Gráf renderelés
                if (data.graph_nodes && data.graph_edges) {
                    document.getElementById('graph-stats').innerText = `Csomópontok: ${data.graph_nodes.length} | Kapcsolatok: ${data.graph_edges.length}`;
                    renderKnowledgeGraph(data.graph_nodes, data.graph_edges);
                }

                // Memória stream
                document.getElementById('memory-stats').innerText = `Sorok: ${data.memory_stats.lines} | Méret: ${data.memory_stats.size_kb} KB`;
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

    let telemetryChartInstance = null;

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

    let currentMctsDataStr = "";

    function renderMCTSTree(treeData) {
        // Csak akkor rajzoljuk újra, ha változott az adat
        const newDataStr = JSON.stringify(treeData);
        if (newDataStr === currentMctsDataStr) return;
        currentMctsDataStr = newDataStr;

        const container = document.getElementById('mcts-graph');
        container.innerHTML = ''; // Törlés

        const width = container.clientWidth;
        const height = 500;
        const margin = {top: 20, right: 120, bottom: 20, left: 120};

        const svg = d3.select("#mcts-graph").append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        const root = d3.hierarchy(treeData);
        const treeLayout = d3.tree().size([height - margin.top - margin.bottom, width - margin.left - margin.right]);
        treeLayout(root);

        // Links
        svg.selectAll(".link")
            .data(root.links())
            .enter().append("path")
            .attr("class", "link")
            .attr("fill", "none")
            .attr("stroke", "#444")
            .attr("stroke-width", 2)
            .attr("d", d3.linkHorizontal().x(d => d.y).y(d => d.x));

        // Nodes
        const node = svg.selectAll(".node")
            .data(root.descendants())
            .enter().append("g")
            .attr("class", "node")
            .attr("transform", d => `translate(${d.y},${d.x})`);

        node.append("circle")
            .attr("r", 8)
            .attr("fill", d => d.data.visits > 0 ? "#4ade80" : "#6b7280")
            .attr("stroke", "#222")
            .attr("stroke-width", 2);

        // Labels (Részletes szövegezés tördelt sorokkal)
        node.append("text")
            .attr("dy", -12)
            .attr("x", d => d.children ? -12 : 12)
            .style("text-anchor", d => d.children ? "end" : "start")
            .attr("fill", "#e0e0e0")
            .style("font-size", "11px")
            .each(function(d) {
                let textStr = d.data.state || d.data.action || "Root";
                const words = textStr.split(' ');
                let line = '';
                let yOffset = 0;
                const textElement = d3.select(this);
                textElement.text('');

                for (let i = 0; i < words.length; i++) {
                    const testLine = line + words[i] + ' ';
                    if (testLine.length > 40) {
                        textElement.append("tspan").attr("x", d.children ? -12 : 12).attr("dy", yOffset === 0 ? 0 : "1.1em").text(line);
                        line = words[i] + ' ';
                        yOffset += 1;
                    } else {
                        line = testLine;
                    }
                }
                textElement.append("tspan").attr("x", d.children ? -12 : 12).attr("dy", yOffset === 0 ? 0 : "1.1em").text(line);
            });

        // Values (Visits / Reward)
        node.append("text")
            .attr("dy", 15)
            .attr("x", 0)
            .style("text-anchor", "middle")
            .attr("fill", "#facc15")
            .style("font-size", "10px")
            .text(d => `V: ${d.data.visits || 0} | W: ${(d.data.value || 0).toFixed(2)}`);
    }

    let currentGraphDataStr = "";
    let graphSimulation = null;

    function renderKnowledgeGraph(nodes, edges) {
        const newDataStr = JSON.stringify(nodes.map(n => n.id)) + JSON.stringify(edges.map(e => e.source_id + '-' + e.target_id));
        if (newDataStr === currentGraphDataStr) return;
        currentGraphDataStr = newDataStr;

        const container = document.getElementById('kg-graph');
        container.innerHTML = '';

        const width = container.clientWidth;
        const height = 600;

        const svg = d3.select("#kg-graph").append("svg")
            .attr("width", width)
            .attr("height", height)
            .call(d3.zoom().on("zoom", (event) => {
               svgGroup.attr("transform", event.transform);
            }));

        const svgGroup = svg.append("g");

        // D3 requires "source" and "target" to be object references or ids
        // We map SQLite edge references (source_id, target_id) to the node objects
        const d3Nodes = nodes.map(d => Object.create(d));
        const d3Edges = edges.map(d => {
            return {
                source: d.source_id,
                target: d.target_id,
                relationship: d.relationship
            };
        });

        if (graphSimulation) graphSimulation.stop();

        graphSimulation = d3.forceSimulation(d3Nodes)
            .force("link", d3.forceLink(d3Edges).id(d => d.id).distance(150))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2));

        // Links
        const link = svgGroup.append("g")
            .attr("stroke", "#555")
            .attr("stroke-opacity", 0.6)
            .selectAll("line")
            .data(d3Edges)
            .join("line")
            .attr("stroke-width", 2);

        // Edge Labels
        const linkText = svgGroup.append("g")
            .selectAll("text")
            .data(d3Edges)
            .join("text")
            .attr("font-size", 10)
            .attr("fill", "#fbbf24")
            .text(d => d.relationship);

        // Nodes
        const node = svgGroup.append("g")
            .selectAll("g")
            .data(d3Nodes)
            .join("g")
            .call(drag(graphSimulation));

        node.append("circle")
            .attr("r", 15)
            .attr("fill", d => {
                // Egészségi/Státusz logika szimulálása név/típus alapján
                if(d.name.includes("Error") || d.name.includes("Fail")) return '#ef4444'; // Piros (Hibás)
                if(d.name.includes("Llama") || d.type === 'System') return '#3b82f6'; // Kék (Mag)
                if(d.type === 'Module' || d.type === 'Component') return '#10b981'; // Zöld (Aktív/OK)
                if(d.type === 'SwarmJob') return '#f59e0b'; // Sárga (Folyamatban/Várakozó)
                return '#6b7280'; // Szürke (Inaktív/Ismeretlen)
            })
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5);

        // Node Labels
        node.append("text")
            .attr("x", 18)
            .attr("y", "0.31em")
            .text(d => d.name)
            .attr("fill", "#fff")
            .style("font-size", "12px");

        // Node Tooltip (Description)
        node.append("title")
            .text(d => `${d.type}: ${d.description}`);

        graphSimulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            linkText
                .attr("x", d => (d.source.x + d.target.x) / 2)
                .attr("y", d => (d.source.y + d.target.y) / 2);

            node
                .attr("transform", d => `translate(${d.x},${d.y})`);
        });

        function drag(simulation) {
          function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
          }
          function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
          }
          function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
          }
          return d3.drag()
              .on("start", dragstarted)
              .on("drag", dragged)
              .on("end", dragended);
        }
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
    # 1. Alapértelmezett kimeneti változók (biztonságos inicializálás)
    stats = {"total": 0, "avg_time": 0, "error_rate": 0}
    telemetry_rows = []
    guardrails_html = "Nincs adat"
    mcts_latest = {}

    # 2. Közös, egyszeri adatbázis megnyitás (mode=ro) File descriptor szivárgás ellen védve
    if os.path.exists(DB_PATH):
        conn = None
        try:
            db_uri = f"file:{DB_PATH}?mode=ro"
            conn = sqlite3.connect(db_uri, uri=True, timeout=5.0)
            c = conn.cursor()

            # --- Alap statisztikák ---
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

            # --- Utolsó hívások ---
            c.execute("SELECT timestamp, tool_name, args, execution_time_ms, status, error_msg FROM mcp_logs ORDER BY id DESC LIMIT 20")
            for r in c.fetchall():
                ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r[0]))
                telemetry_rows.append({
                    "time": ts_str,
                    "tool_name": r[1],
                    "args_raw": r[2],
                    "duration": r[3],
                    "status": r[4],
                    "error": html.escape(str(r[5])) if r[5] else ""
                })

            # --- MCTS Data ---
            c.execute("SELECT mcts_data FROM mcp_logs WHERE tool_name='deep_planning' AND status='success' AND mcts_data IS NOT NULL ORDER BY id DESC LIMIT 1")
            mcts_row = c.fetchone()
            if mcts_row and mcts_row[0]:
                try:
                    mcts_latest = json.loads(mcts_row[0])
                except Exception as ex:
                    mcts_latest = {"name": f"Hiba a JSON parszolásban: {ex}"}

            # --- Guardrails Telemetria ---
            c.execute("SELECT COUNT(*), SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) FROM mcp_logs WHERE tool_name='write_file_mcp'")
            write_total, write_errs = c.fetchone()
            write_errs = write_errs if write_errs else 0
            write_total = write_total if write_total else 0
            success_rate = ((write_total - write_errs) / write_total * 100) if write_total > 0 else 100
            color = "text-success" if success_rate > 90 else ("text-warning" if success_rate > 70 else "text-danger")
            guardrails_html = f"<div>ADR & AST Validációs Arány: <b class='{color}'>{success_rate:.1f}%</b></div>"
            guardrails_html += f"<div>Összes fájl írási kísérlet: <b>{write_total}</b></div>"
            guardrails_html += f"<div>Blokkolt / Hiba: <b class='text-danger'>{write_errs}</b></div>"

        except sqlite3.Error as e:
            mcts_latest = {"name": f"Adatbázis hiba: {e}"}
            guardrails_html = f"Adatbázis hiba: {e}"
        except Exception as e:
            mcts_latest = {"name": f"Ismeretlen hiba: {e}"}
        finally:
            if conn:
                conn.close()

    # 3. JSONL Memória Lekérése OOM (Out Of Memory) védelemmel
    # A readlines() helyett egy külső eszközt (tail) vagy egy hatékony soronkénti puffert használunk
    memory_entries = []
    memory_stats = {"lines": 0, "size_kb": 0}
    reflection_html = "<span class='text-muted'>Jelenleg nincs új rendszer-reflexió.</span>"
    if os.path.exists(MEMORY_PATH):
        try:
            size_kb = os.path.getsize(MEMORY_PATH) / 1024.0
            memory_stats["size_kb"] = round(size_kb, 2)

            # Visszafelé olvassuk a fájlt anélkül, hogy a teljes RAM-ot teleszemetelnénk a readlines()-szal.
            import subprocess
            tail_lines = subprocess.check_output(["tail", "-n", "1000", MEMORY_PATH]).decode('utf-8').splitlines()
            memory_stats["lines"] = len(tail_lines) # Becsült utolsó X sor alapján, valós sorszám helyett a gyorsaságért

            found_reflection = False
            for line in reversed(tail_lines):
                if not line.strip():
                    continue
                try:
                    mem_obj = json.loads(line)
                    # Elmentjük az utolsó 15 elemet
                    if len(memory_entries) < 15:
                        if 'content' in mem_obj:
                            mem_obj['content'] = html.escape(str(mem_obj['content']))
                        memory_entries.append(mem_obj)

                    # Kikeressük az utolsó reflexiót
                    if not found_reflection and mem_obj.get('category') in ['Context_Summary', 'Reflection', 'Architecture_Pipeline_Update', 'Guardrail_Block']:
                        ts = mem_obj.get('timestamp', '')
                        cat = html.escape(str(mem_obj.get('category', '')))
                        cont = html.escape(str(mem_obj.get('content', '')))
                        reflection_html = f"<span class='text-secondary'>[{ts}]</span> <b class='text-danger'>[{cat}]</b><br><i style='color: #e2e8f0;'>\"{cont}\"</i>"
                        found_reflection = True
                except Exception:
                    pass # Zombie JSON védelem
        except Exception as e:
            err_id = str(uuid.uuid4())[:8]
            logging.error(f"Error [{err_id}] in Memory parsing: {e}", exc_info=True)
            reflection_html = f"<span class='text-danger'>Rendszerhiba a reflexiók betöltésekor. ID: Err-{err_id}</span>"

    blueprint_html = ""
    bp_path = "/home/misi/Jules_ICA_Builder/blueprint.md"
    try:
        if os.path.exists(bp_path):
            modified_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(bp_path)))
            with open(bp_path, 'r', encoding='utf-8') as bpf:
                bp_content = bpf.read()
                # Egyszerű ADR szekció ellenőrzés
                has_context = "## Context" in bp_content
                has_decision = "## Decision" in bp_content
                has_status = "## Status" in bp_content
                valid = has_context and has_decision and has_status

                v_color = "text-success" if valid else "text-danger"
                v_text = "ADR Valid" if valid else "Sérült/Hiányos ADR"
                blueprint_html = f"<div>Státusz: <b class='{v_color}'>{v_text}</b></div>"
                blueprint_html += f"<div>Utolsó frissítés: <span class='text-muted'>{modified_time}</span></div>"
        else:
            blueprint_html = "<div class='text-danger'>Nincs blueprint.md (Design Fázis hiányzik!)</div>"
    except Exception as e:
        blueprint_html = f"Hiba: {e}"

    # Extra adatok (Health, Inbox) - Biztonságos (Zero Trust) implementáció psutil használatával
    system_health_str = "Nem elérhető"
    try:
        global last_cpu_time, last_cpu_percent
        current_time = time.time()

        # CPU frissítése maximum 1 másodpercenként a 0.0% anomália elkerülésére
        if current_time - last_cpu_time > 1.0:
            last_cpu_percent = psutil.cpu_percent(interval=None)
            last_cpu_time = current_time

        cpu = f"{last_cpu_percent}%"
        mem_info = psutil.virtual_memory()
        mem = f"{mem_info.percent}%"
        disk_info = shutil.disk_usage("/")
        disk = f"{(disk_info.used / disk_info.total) * 100:.1f}%"
        system_health_str = f"CPU Használat: {cpu}\nRAM Használat: {mem}\nLemez (/): {disk}"
    except Exception as e:
        err_id = str(uuid.uuid4())[:8]
        logging.error(f"Error [{err_id}] in System Health Check: {e}", exc_info=True)
        system_health_str = f"Rendszerállapot lekérdezés sikertelen. ID: Err-{err_id}"

    inbox_str = ""
    inbox_dir = "/home/misi/Jules_ICA_Builder/inbox"
    try:
        if os.path.exists(inbox_dir):
            files = [f for f in os.listdir(inbox_dir) if f.startswith("msg_") and f.endswith(".txt")]
            if files:
                for f in files:
                    filepath = os.path.join(inbox_dir, f)
                    with open(filepath, 'r', encoding='utf-8') as file:
                        inbox_str += f"[{f}]: {html.escape(file.read()[:50])}...\n"
            else:
                inbox_str = "Nincsenek várakozó Swarm üzenetek."
        else:
            inbox_str = "Inbox könyvtár nem létezik."
    except Exception as e:
        inbox_str = f"Hiba az Inbox olvasásakor: {e}"

    # 4. Tudásgráf lekérése
    graph_nodes = []
    graph_edges = []
    GRAPH_DB_PATH = "/home/misi/Jules_ICA_Builder/ica_knowledge_graph.db"
    if os.path.exists(GRAPH_DB_PATH):
        conn_g = None
        try:
            db_uri_graph = f"file:{GRAPH_DB_PATH}?mode=ro"
            conn_g = sqlite3.connect(db_uri_graph, uri=True, timeout=5.0)
            cg = conn_g.cursor()
            cg.execute("SELECT id, name, type, description FROM entities")
            for r in cg.fetchall():
                graph_nodes.append({"id": r[0], "name": r[1], "type": r[2], "description": r[3]})

            cg.execute("SELECT source_id, target_id, relationship FROM edges")
            for r in cg.fetchall():
                graph_edges.append({"source_id": r[0], "target_id": r[1], "relationship": r[2]})
        except Exception as e:
            err_id = str(uuid.uuid4())[:8]
            logging.error(f"Error [{err_id}] in Graph DB: {e}", exc_info=True)
        finally:
            if conn_g:
                conn_g.close()

    return jsonify({
        "stats": stats,
        "telemetry": telemetry_rows,
        "memory": memory_entries,
        "guardrails_html": guardrails_html if 'guardrails_html' in locals() else "",
        "blueprint_html": blueprint_html if 'blueprint_html' in locals() else "",
        "reflection_html": reflection_html if 'reflection_html' in locals() else "",
        "system_health": system_health_str if 'system_health_str' in locals() else "",
        "swarm_inbox": inbox_str if 'inbox_str' in locals() else "",
        "mcts_latest": mcts_latest if 'mcts_latest' in locals() else {},
        "graph_nodes": graph_nodes if 'graph_nodes' in locals() else [],
        "graph_edges": graph_edges if 'graph_edges' in locals() else [],
        "memory_stats": memory_stats
    })

if __name__ == '__main__':
    # Éles WSGI szerver használata a fejlesztői helyett
    from waitress import serve
    print("🚀 Jules ICA Web Monitor elindítva (Waitress WSGI). Elérhető: http://127.0.0.1:8080")
    serve(app, host='127.0.0.1', port=8080)
