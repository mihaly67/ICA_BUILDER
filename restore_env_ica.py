#!/usr/bin/env python3
"""
Jules ICA System Környezet Inicializáló
Betölti a függőségeket, integrálja a VPS Llama modelleket, és elindítja a memória szinkronizálót.
Ez a script adja meg a "Runtime Environment" (Környezet) szabályait és eszközeit.
"""
import os
import subprocess
import sys

def install_dependencies():
    print("🔧 ICA Függőségek telepítése...")
    try:
        # Hozzáadjuk a '--break-system-packages' paramétert ha szükséges újabb pip-nél, vagy sudo-val globálisan.
        # De biztonságosabb simán az aktuális pyenv / virtualenv pipjét használni:
        subprocess.run([sys.executable, "-m", "pip", "install", "mcp", "paramiko", "python-dotenv"], check=True)
        # Az sshpass telepítése az apt-get használatával:
        subprocess.run("sudo apt-get update && sudo apt-get install -y sshpass", shell=True, check=True)
        print("✅ Függőségek telepítve.")
    except Exception as e:
        print(f"⚠️ Hiba a függőségek telepítésekor: {e}")

def check_vps_llama_status():
    """
    Ellenőrzi, hogy a környezet (VPS) Llama AI képességei elérhetők-e.
    Ha igen, regisztrálja őket mint lokális skillek.
    """
    print("🤖 VPS Llama/Ollama kapcsolat ellenőrzése...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    llama_client_path = os.path.join(script_dir, "tools", "skills", "vps_llama_client.py")

    if os.path.exists(llama_client_path):
        try:
            cmd = [sys.executable, llama_client_path, "Ping! Él a kapcsolat?", "--model", "qwen2.5:1.5b"]
            env = os.environ.copy()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)

            if "LLAMA VÁLASZ" in result.stdout:
                print("🟢 SIKER: VPS Ollama modell (qwen2.5/llama3) integrálva a környezetbe!")
                print("   👉 Használati utasítás az Agent-nek: Ha olcsó másodlagos ellenőrzésre vagy logelemzésre van szükség, használd a `python3 tools/skills/vps_llama_client.py` parancsot!")
                print('   👉 Keresés a felcímkézett VPS RAG repókban: `python3 tools/skills/mcp_repo_search.py "kulcsszó"`')
            else:
                print("🟡 FIGYELEM: A VPS Llama API nem válaszolt vagy timeoutolt. Ez az al-képesség most nem elérhető.")
                print(f"   [Debug]: {result.stderr}")
        except Exception as e:
            print(f"🟡 FIGYELEM: Hiba a Llama kapcsolat tesztelésekor: {e}")
    else:
        print("🟡 Nincs telepítve a Llama Kliens tool.")

def register_rag_environments():
    print("📚 RAG Adatbázis Környezeti Változók beállítása (.env fájlba)...")
    env_content = "MAIN_RAG_PATH=/home/misi/Rag_epites, chatbot_csv_data_llm_RAG/\n"
    env_content += "DEV_RAG_PATH=/home/misi/BRAIN2_DEV_RAG/\n"

    # Hogy ne ismétlődjenek a sorok, ellenőrizzük, megvannak-e már:
    existing_content = ""
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            existing_content = f.read()

    if "MAIN_RAG_PATH" not in existing_content:
        with open(".env", "a") as f:
             f.write(env_content)
        print("✅ RAG útvonalak perzisztens regisztrálása sikeres (.env).")
    else:
        print("✅ RAG útvonalak már regisztrálva vannak.")

def main():
    print("=== 🐝 JULES ICA SYSTEM INITIALIZATION ===")
    install_dependencies()

    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("🧠 Memória inicializálása és VPS szinkronizáció...")
    memory_manager_path = os.path.join(script_dir, "ENVIRONMENT_SETUP", "agent_memory_manager.py")
    if os.path.exists(memory_manager_path):
        subprocess.run([sys.executable, memory_manager_path, "--action", "start_session"])

    check_vps_llama_status()
    register_rag_environments()

    print("\n🚀 Jules ICA Környezet élesítve és felszerelve a VPS képességekkel!")
    print("Kérlek, olvasd el az AGENTS_ICA.md-t és kezdd el a munkát a System 2 protokoll alapján!")

if __name__ == "__main__":
    main()
