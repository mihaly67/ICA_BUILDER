import re

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# Make sure graph is updated when new nodes are added
# Modify the renderKnowledgeGraph JS logic slightly to not strictly ignore updates
old_graph_check = '''        const newDataStr = JSON.stringify(nodes) + JSON.stringify(edges);
        if (newDataStr === currentGraphDataStr) return;
        currentGraphDataStr = newDataStr;'''

new_graph_check = '''        const newDataStr = JSON.stringify(nodes.map(n => n.id)) + JSON.stringify(edges.map(e => e.source_id + '-' + e.target_id));
        if (newDataStr === currentGraphDataStr) return;
        currentGraphDataStr = newDataStr;'''

content = content.replace(old_graph_check, new_graph_check)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
