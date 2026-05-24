import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# 1. MCTS Részletes szövegezés:
# A node.append("text") -nél beállítjuk, hogy a teljes szöveget írja ki sortörésekkel
old_mcts_text = '''        // Labels
        node.append("text")
            .attr("dy", -12)
            .attr("x", d => d.children ? -8 : 8)
            .style("text-anchor", d => d.children ? "end" : "start")
            .attr("fill", "#e0e0e0")
            .text(d => {
                let txt = d.data.state || d.data.action || "Root";
                if(txt.length > 30) txt = txt.substring(0, 30) + "...";
                return txt;
            });'''

new_mcts_text = '''        // Labels (Részletes szövegezés tördelt sorokkal)
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
            });'''

content = content.replace(old_mcts_text, new_mcts_text)

# 2. Ördög Ügyvédje (Önreflexió) Real-time frissülés javítása
# Előzőleg a 'memory_entries'-ből szűrtük a Reflection-t, aminek maximális elemszáma (15) miatt
# kieshettek az utolsó reflexiók, ha azokat friss MCTS vagy egyéb logok elnyomták.
old_reflection = '''    reflection_html = ""
    try:
        if memory_entries:
            # Keresünk 'Reflection', 'Critic', 'Error', 'Guardrail' kategóriákat az utolsó memóriákban
            reflections = [m for m in memory_entries if m.get('category') in ['Context_Summary', 'Reflection', 'Architecture_Pipeline_Update', 'Guardrail_Block']]
            if reflections:
                latest_ref = reflections[-1]
                ts = latest_ref.get('timestamp', '').split('T')[0]
                cat = latest_ref.get('category', '')
                content = latest_ref.get('content', '')
                reflection_html = f"<span class='text-secondary'>[{ts}]</span> <b class='text-danger'>[{cat}]</b><br><i style='color: #e2e8f0;'>\\\"{content}\\\"</i>"
            else:
                reflection_html = "<span class='text-muted'>Jelenleg nincs új rendszer-reflexió.</span>"
    except Exception as e:
        reflection_html = f"Hiba: {e}"'''

new_reflection = '''    reflection_html = ""
    try:
        # A teljes memóriát átnézzük visszafelé, hogy MÁR NE vesszen el a 15-ös korlát miatt
        if os.path.exists(MEMORY_PATH):
            with open(MEMORY_PATH, "r", encoding="utf-8") as mf:
                all_lines = mf.readlines()
                for line in reversed(all_lines):
                    try:
                        mem_obj = json.loads(line)
                        if mem_obj.get('category') in ['Context_Summary', 'Reflection', 'Architecture_Pipeline_Update', 'Guardrail_Block']:
                            ts = mem_obj.get('timestamp', '')
                            cat = mem_obj.get('category', '')
                            cont = mem_obj.get('content', '')
                            reflection_html = f"<span class='text-secondary'>[{ts}]</span> <b class='text-danger'>[{cat}]</b><br><i style='color: #e2e8f0;'>\\\"{cont}\\\"</i>"
                            break  # Megtaláltuk a legutolsót
                    except:
                        pass
        if not reflection_html:
            reflection_html = "<span class='text-muted'>Jelenleg nincs új rendszer-reflexió.</span>"
    except Exception as e:
        reflection_html = f"Hiba: {e}"'''

content = content.replace(old_reflection, new_reflection)


with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
