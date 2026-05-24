import re

with open('vps_llama_client.py', 'r') as f:
    content = f.read()

# Add keep_alive to the Ollama API call payload so the model stays loaded in memory longer
old_payload = '''    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "system": args.system,
        "stream": False,
        "options": {
            "temperature": 0.7
        }
    }'''

new_payload = '''    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "system": args.system,
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.7,
            "num_predict": 100
        }
    }'''

content = content.replace(old_payload, new_payload)

with open('vps_llama_client.py', 'w') as f:
    f.write(content)
