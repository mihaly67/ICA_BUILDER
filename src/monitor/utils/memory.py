import os
import json
import logging
import uuid
import html
import subprocess
import time

MEMORY_PATH = "/home/misi/Jules_ICA_Builder/Knowledge_Base/agent_memory.jsonl"
BP_PATH = "/home/misi/Jules_ICA_Builder/blueprint.md"

def get_memory_stats_and_entries():
    memory_entries = []
    memory_stats = {"lines": 0, "size_kb": 0}
    reflection_html = "<span class='text-muted'>Jelenleg nincs új rendszer-reflexió.</span>"

    if os.path.exists(MEMORY_PATH):
        try:
            size_kb = os.path.getsize(MEMORY_PATH) / 1024.0
            memory_stats["size_kb"] = round(size_kb, 2)

            tail_lines = subprocess.check_output(["tail", "-n", "1000", MEMORY_PATH]).decode('utf-8').splitlines()
            memory_stats["lines"] = len(tail_lines)

            found_reflection = False
            for line in reversed(tail_lines):
                if not line.strip():
                    continue
                try:
                    mem_obj = json.loads(line)
                    if len(memory_entries) < 15:
                        if 'content' in mem_obj:
                            mem_obj['content'] = html.escape(str(mem_obj['content']))
                        memory_entries.append(mem_obj)

                    if not found_reflection and mem_obj.get('category') in ['Context_Summary', 'Reflection', 'Architecture_Pipeline_Update', 'Guardrail_Block']:
                        ts = mem_obj.get('timestamp', '')
                        cat = html.escape(str(mem_obj.get('category', '')))
                        cont = html.escape(str(mem_obj.get('content', '')))
                        reflection_html = f"<span class='text-secondary'>[{ts}]</span> <b class='text-danger'>[{cat}]</b><br><i style='color: #e2e8f0;'>\"{cont}\"</i>"
                        found_reflection = True
                except Exception:
                    pass
        except Exception as e:
            err_id = str(uuid.uuid4())[:8]
            logging.error(f"Error [{err_id}] in Memory parsing: {e}", exc_info=True)
            reflection_html = f"<span class='text-danger'>Rendszerhiba a reflexiók betöltésekor. ID: Err-{err_id}</span>"

    return memory_entries, memory_stats, reflection_html

def get_blueprint_status():
    blueprint_html = ""
    try:
        if os.path.exists(BP_PATH):
            modified_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(BP_PATH)))
            with open(BP_PATH, 'r', encoding='utf-8') as bpf:
                bp_content = bpf.read()
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

    return blueprint_html
