#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import threading

def run_reminder_loop():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    restore_script = os.path.join(project_root, "restore_env_ica.py")

    print(f"🔄 Amnézia elleni memóriaszolgáltatás elindítva (pid: {os.getpid()})")
    while True:
        try:
            # Csak a szinkronizálót hívjuk meg közvetlenül a memóriafájl frissítése miatt,
            # de a restore_env_ica.py is hívható, viszont az a hálózati ellenőrzések miatt megszakadhat
            print("🧠 Memória környezet frissítés emlékeztető futtatása...")

            # Betöltjük a memóriát az agent_memory_manager segítségével
            memory_manager = os.path.join(script_dir, "agent_memory_manager.py")
            if os.path.exists(memory_manager):
                subprocess.run([sys.executable, memory_manager, "--action", "read", "--limit", "1"], capture_output=True)

        except Exception as e:
            pass
        # Minden órában fut
        time.sleep(3600)

if __name__ == "__main__":
    run_reminder_loop()
