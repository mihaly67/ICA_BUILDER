import re
import sys

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# Add D3.js and MCTS visualization container
html_head = '''    <style>'''
new_html_head = '''    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>'''
content = content.replace(html_head, new_html_head)

# Add MCTS Card
html_panels = '''        <!-- Memória Panel -->'''
new_html_panels = '''        <!-- MCTS Vizualizáció Panel -->
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

        <!-- Memória Panel -->'''
content = content.replace(html_panels, new_html_panels)

# Update the fetch JS logic
fetch_logic = '''                // Telemetria tábla'''
new_fetch_logic = '''                // MCTS fa renderelés ha van adat
                const latestMctsData = data.mcts_latest;
                if (latestMctsData && Object.keys(latestMctsData).length > 0) {
                    document.getElementById('mcts-status').innerText = "Utolsó tervezés megjelenítve";
                    renderMCTSTree(latestMctsData);
                }

                // Telemetria tábla'''
content = content.replace(fetch_logic, new_fetch_logic)


# Add D3 logic at the end of script
end_script = '''    // Frissítés másodpercenként'''
new_end_script = '''    let currentMctsDataStr = "";

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

        // Labels
        node.append("text")
            .attr("dy", -12)
            .attr("x", d => d.children ? -8 : 8)
            .style("text-anchor", d => d.children ? "end" : "start")
            .attr("fill", "#e0e0e0")
            .text(d => {
                let txt = d.data.state || d.data.action || "Root";
                if(txt.length > 30) txt = txt.substring(0, 30) + "...";
                return txt;
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

    // Frissítés másodpercenként'''
content = content.replace(end_script, new_end_script)

# Add python route handling for MCTS
route_logic = '''        except Exception as e:
            print("DB hiba:", e)'''

new_route_logic = '''            # Get latest MCTS data
            c.execute("SELECT mcts_data FROM mcp_logs WHERE tool_name='deep_planning' AND status='success' AND mcts_data IS NOT NULL ORDER BY id DESC LIMIT 1")
            mcts_row = c.fetchone()
            mcts_latest = {}
            if mcts_row and mcts_row[0]:
                try:
                    mcts_latest = json.loads(mcts_row[0])
                except:
                    pass
        except Exception as e:
            print("DB hiba:", e)'''

content = content.replace(route_logic, new_route_logic)

json_return = '''        "telemetry": telemetry_rows,
        "memory": memory_entries
    })'''

new_json_return = '''        "telemetry": telemetry_rows,
        "memory": memory_entries,
        "mcts_latest": mcts_latest if 'mcts_latest' in locals() else {}
    })'''
content = content.replace(json_return, new_json_return)


with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
