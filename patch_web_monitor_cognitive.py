import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# 1. Bővítjük a UI-t a Kognitív Folyamatok paneljével (Önreflexió, Blueprint státusz, Guardrails)
old_html = '''        <!-- System Health & Inbox (ÚJ) -->'''
new_html = '''        <!-- Kognitív Pipeline & System Állapot (ÚJ) -->
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

        <!-- System Health & Inbox (ÚJ) -->'''
content = content.replace(old_html, new_html)

# 2. JS Update beállítása
old_js = '''                // Rendszer állapot'''
new_js = '''                // Kognitív Pipeline adatok
                document.getElementById('guardrails-status').innerHTML = data.guardrails_html || "Nincs adat";
                document.getElementById('blueprint-status').innerHTML = data.blueprint_html || "Nincs adat";
                document.getElementById('reflection-status').innerHTML = data.reflection_html || "Nincsenek aktív önreflexió bejegyzések.";

                // Rendszer állapot'''
content = content.replace(old_js, new_js)

# 3. Python Backend logika kiterjesztése a memóriából és fájlokból történő olvasáshoz
old_api = '''    # Extra adatok (Health, Inbox)'''
new_api = '''    # Kognitív Pipeline Adatok (Guardrails, Blueprint, Önreflexió)
    guardrails_html = ""
    try:
        # Guardrails telemetria olvasása
        c.execute("SELECT COUNT(*), SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) FROM mcp_logs WHERE tool_name='write_file_mcp'")
        write_total, write_errs = c.fetchone()
        write_errs = write_errs if write_errs else 0
        write_total = write_total if write_total else 0
        success_rate = ((write_total - write_errs) / write_total * 100) if write_total > 0 else 100
        color = "text-success" if success_rate > 90 else ("text-warning" if success_rate > 70 else "text-danger")
        guardrails_html = f"<div>ADR & AST Validációs Arány: <b class='{color}'>{success_rate:.1f}%</b></div>"
        guardrails_html += f"<div>Összes fájl írási kísérlet: <b>{write_total}</b></div>"
        guardrails_html += f"<div>Blokkolt / Hiba: <b class='text-danger'>{write_errs}</b></div>"
    except Exception as e:
        guardrails_html = f"Hiba: {e}"

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

    reflection_html = ""
    try:
        if memory_entries:
            # Keresünk 'Reflection', 'Critic', 'Error', 'Guardrail' kategóriákat az utolsó memóriákban
            reflections = [m for m in memory_entries if m.get('category') in ['Context_Summary', 'Reflection', 'Architecture_Pipeline_Update', 'Guardrail_Block']]
            if reflections:
                latest_ref = reflections[-1]
                ts = latest_ref.get('timestamp', '').split('T')[0]
                cat = latest_ref.get('category', '')
                content = latest_ref.get('content', '')
                reflection_html = f"<span class='text-secondary'>[{ts}]</span> <b class='text-danger'>[{cat}]</b><br><i style='color: #e2e8f0;'>\"{content}\"</i>"
            else:
                reflection_html = "<span class='text-muted'>Jelenleg nincs új rendszer-reflexió.</span>"
    except Exception as e:
        reflection_html = f"Hiba: {e}"

    # Extra adatok (Health, Inbox)'''
content = content.replace(old_api, new_api)

# 4. JSON válasz frissítése
old_json = '''        "system_health": system_health_str if 'system_health_str' in locals() else "",'''
new_json = '''        "guardrails_html": guardrails_html if 'guardrails_html' in locals() else "",
        "blueprint_html": blueprint_html if 'blueprint_html' in locals() else "",
        "reflection_html": reflection_html if 'reflection_html' in locals() else "",
        "system_health": system_health_str if 'system_health_str' in locals() else "",'''
content = content.replace(old_json, new_json)

# 5. Gráf node szín frissítés az "egészség" bemutatására
old_graph_color = '''            .attr("fill", d => {
                if(d.type === 'System') return '#3b82f6';
                if(d.type === 'Module') return '#10b981';
                if(d.type === 'Component') return '#8b5cf6';
                if(d.type === 'SwarmJob') return '#ef4444';
                return '#6b7280';
            })'''

new_graph_color = '''            .attr("fill", d => {
                // Egészségi/Státusz logika szimulálása név/típus alapján
                if(d.name.includes("Error") || d.name.includes("Fail")) return '#ef4444'; // Piros (Hibás)
                if(d.name.includes("Llama") || d.type === 'System') return '#3b82f6'; // Kék (Mag)
                if(d.type === 'Module' || d.type === 'Component') return '#10b981'; // Zöld (Aktív/OK)
                if(d.type === 'SwarmJob') return '#f59e0b'; // Sárga (Folyamatban/Várakozó)
                return '#6b7280'; // Szürke (Inaktív/Ismeretlen)
            })'''
content = content.replace(old_graph_color, new_graph_color)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
