import re
import sys

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# Add Graph visualization container below MCTS
html_panels = '''        <!-- Memória Panel -->'''
new_html_panels = '''        <!-- Tudásgráf Vizualizáció Panel -->
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

        <!-- Memória Panel -->'''
content = content.replace(html_panels, new_html_panels)

# Update fetch logic to call renderGraph
fetch_logic = '''                // Memória stream'''
new_fetch_logic = '''                // Gráf renderelés
                if (data.graph_nodes && data.graph_edges) {
                    document.getElementById('graph-stats').innerText = `Csomópontok: ${data.graph_nodes.length} | Kapcsolatok: ${data.graph_edges.length}`;
                    renderKnowledgeGraph(data.graph_nodes, data.graph_edges);
                }

                // Memória stream'''
content = content.replace(fetch_logic, new_fetch_logic)

# D3 Force Directed Graph JS code
end_script = '''    // Frissítés másodpercenként'''
new_end_script = '''    let currentGraphDataStr = "";
    let graphSimulation = null;

    function renderKnowledgeGraph(nodes, edges) {
        const newDataStr = JSON.stringify(nodes) + JSON.stringify(edges);
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
                if(d.type === 'System') return '#3b82f6';
                if(d.type === 'Module') return '#10b981';
                if(d.type === 'Component') return '#8b5cf6';
                if(d.type === 'SwarmJob') return '#ef4444';
                return '#6b7280';
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

    // Frissítés másodpercenként'''
content = content.replace(end_script, new_end_script)

# Add python route handling for Graph DB
route_logic = '''    return jsonify({'''

new_route_logic = '''    # 4. Tudásgráf lekérése
    graph_nodes = []
    graph_edges = []
    GRAPH_DB_PATH = "/home/misi/Jules_ICA_Builder/ica_knowledge_graph.db"
    if os.path.exists(GRAPH_DB_PATH):
        try:
            conn_g = sqlite3.connect(GRAPH_DB_PATH)
            cg = conn_g.cursor()
            cg.execute("SELECT id, name, type, description FROM entities")
            for r in cg.fetchall():
                graph_nodes.append({"id": r[0], "name": r[1], "type": r[2], "description": r[3]})

            cg.execute("SELECT source_id, target_id, relationship FROM edges")
            for r in cg.fetchall():
                graph_edges.append({"source_id": r[0], "target_id": r[1], "relationship": r[2]})
            conn_g.close()
        except Exception as e:
            print("Graph DB hiba:", e)

    return jsonify({'''
content = content.replace(route_logic, new_route_logic)

json_return = '''        "memory": memory_entries,
        "mcts_latest": mcts_latest if 'mcts_latest' in locals() else {}'''

new_json_return = '''        "memory": memory_entries,
        "mcts_latest": mcts_latest if 'mcts_latest' in locals() else {},
        "graph_nodes": graph_nodes if 'graph_nodes' in locals() else [],
        "graph_edges": graph_edges if 'graph_edges' in locals() else []'''
content = content.replace(json_return, new_json_return)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
