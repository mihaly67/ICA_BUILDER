import time
import os
import subprocess
from datetime import datetime

# Budapest Timezone setting can be configured environment-wide
# For simulation, we assume local time is synced or we log explicitly
VPS_INBOX_DIR = "/home/misi/Jules_mx/temp/inbox/"
LOCAL_TEMP_DIR = "./temp_inbox"

def check_for_stimulus():
    """
    Keresi a külső ingereket (pl. fájl alapú bemenet a felhasználótól vagy más agenttől).
    Ha nincs inger, visszaadhat egy "Self-Reflection" (Önreflexió) triggert,
    hogy az LLM ne aludjon el, hanem elemezze a saját memóriáját.
    """
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)
    files = os.listdir(LOCAL_TEMP_DIR)
    if files:
        # Van feldolgozandó feladat
        file_path = os.path.join(LOCAL_TEMP_DIR, files[0])
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        os.remove(file_path)
        return content

    # Ha nincs új feladat, bizonyos időközönként generálunk egy "Idle" feladatot.
    # Ez a "szívdobbanás" ami életben tartja a kognitív folyamatot.
    return "AUTONOMOUS_TRIGGER: Elemezd a legutóbbi regisztereket és keress optimalizálási lehetőségeket (Self-Reflection)."

def run_clock(interval_seconds=60):
    print(f"[{datetime.now()}] 🕰️ Autonóm Órajel (Cognitive Clock) elindítva. Ketyegés: {interval_seconds} másodpercenként.")

    try:
        while True:
            stimulus = check_for_stimulus()

            print(f"\n[{datetime.now()}] ⚡ Inger észlelve: '{stimulus[:50]}...'")
            print(f"[{datetime.now()}] 🧠 Kognitív Pipeline ébresztése...")

            # Az LLM (vagyis az ica_pipeline.py) "felébresztése"
            # Itt az orchestrator átveszi az ember (a "gombnyomogató") szerepét.
            subprocess.run(["python3", "src/cognitive_engine/ica_pipeline.py", stimulus])

            print(f"[{datetime.now()}] 💤 Pipeline végzett. Várakozás a következő órajelre...\n")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nÓrajel leállítva a felhasználó által.")

if __name__ == "__main__":
    # Teszt céljából rövidebb időköz (pl 10 másodperc), élesben lehet 5-10 perc
    run_clock(interval_seconds=10)
