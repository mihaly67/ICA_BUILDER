import sys
import json
import urllib.request
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="The user prompt to send to the model")
    parser.add_argument("--model", default="qwen2.5:1.5b", help="Model name (e.g., qwen2.5:1.5b or llama3.1:8b)")
    parser.add_argument("--system", default="Te egy logikai tervező AI vagy. Légy tömör.", help="System prompt")
    args = parser.parse_args()

    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "system": args.system,
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.7,
            "num_predict": 100
        }
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("LLAMA VÁLASZ")
            print("="*50)
            print(result.get("response", "").strip())
            print("="*50)
    except Exception as e:
        print(f"Error communicating with Ollama: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
