import urllib.request
import json
import time

url = "http://127.0.0.1:11434/api/generate"
payload = {
    "model": "qwen2.5:1.5b",
    "prompt": "Szia, teszt.",
    "stream": False
}

start = time.time()
try:
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as res:
        print("OK", time.time() - start)
except Exception as e:
    print("ERR", e)
