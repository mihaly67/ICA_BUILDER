import os
import sys
import json
import subprocess

# Kicsit elegánsabban oldjuk meg: A VPS-en lévő curl API hívást csomagoljuk be,
# így nem kell port forwardot nyitni (biztonságosabb), csak a meglévő vps_bridge logikát használjuk.

VPS_HOST = os.environ.get("VPS_HOST", "5.189.163.88")
VPS_PWD = os.environ.get("VPS_PWD", "")
VPS_USER = os.environ.get("VPS_USER", "misi")

def query_vps_llama(prompt, model="llama3:latest"):
    """
    Meghívja a VPS-en futó lokális Llama modellt (Ollama) egy prompttal.
    Kiválóan használható al-feladatokhoz (pl. logelemzés, adatbázis összegzés),
    hogy kíméljük a fő LLM tokeneit.
    """
    # A promptot escape-elni kell a shell miatt
    safe_prompt = prompt.replace("'", "'\\''")

    # Payload összeállítása
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False
    })

    # Shell trükk: A JSON idézőjeleit is el kell rejteni a bash elől
    safe_payload = payload.replace("'", "'\\''")

    cmd = f"curl -s -X POST http://localhost:11434/api/generate -H 'Content-Type: application/json' -d '{safe_payload}'"

    # Zero Trust: Public-Key hitelesítés használata sshpass helyett
    ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", f"{VPS_USER}@{VPS_HOST}", cmd]

    env = os.environ.copy()

    try:
        result = subprocess.run(ssh_cmd, check=True, capture_output=True, text=True, env=env)
        response_json = json.loads(result.stdout)
        return response_json.get("response", "Nincs válasz a modelltől.")
    except subprocess.CalledProcessError as e:
        return f"Hiba az SSH hívás során: {e.stderr}"
    except json.JSONDecodeError:
        return f"Hibás JSON válasz érkezett: {result.stdout}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Használat: python3 vps_llama_client.py 'Prompt a Llamának' [--model qwen2.5:1.5b]")
        sys.exit(1)

    prompt = sys.argv[1]
    model = "llama3:latest"
    if "--model" in sys.argv:
        model_idx = sys.argv.index("--model")
        if model_idx + 1 < len(sys.argv):
            model = sys.argv[model_idx + 1]

    print(f"🤖 Kérdezés a VPS Llama modelltől ({model})... Kérlek várj.")
    response = query_vps_llama(prompt, model)
    print("\n--- LLAMA VÁLASZ ---")
    print(response)
