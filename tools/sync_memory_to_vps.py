import os
import time
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logging.basicConfig(filename='memory_sync.log', level=logging.INFO, format='%(asctime)s - %(message)s')

LOCAL_MEMORY_PATH = "Knowledge_Base/agent_memory.jsonl"
VPS_IP = os.environ.get("VPS_IP", "5.189.163.88")
VPS_USER = os.environ.get("VPS_USER", "misi")
VPS_TARGET_DIR = "/home/misi/Jules_ICA_Builder/Knowledge_Base"
SSH_PASS = os.environ.get("SSH_PASS", "")

def sync_memory():
    if not os.path.exists(LOCAL_MEMORY_PATH):
        logging.warning("Nincs helyi memory.jsonl fájl.")
        return

    if not SSH_PASS:
        logging.error("SSH_PASS környezeti változó hiányzik, szinkronizáció megszakítva.")
        return

    try:
        # 1. VPS Chattr Unlock (Zero Trust bypass for sync)
        unlock_cmd = f"sshpass -p '{SSH_PASS}' ssh -o StrictHostKeyChecking=no {VPS_USER}@{VPS_IP} 'sudo -n chattr -a {VPS_TARGET_DIR}/agent_memory.jsonl || true'"
        subprocess.run(unlock_cmd, shell=True, stderr=subprocess.DEVNULL)

        # 2. RSYNC Upload
        rsync_cmd = f"sshpass -p '{SSH_PASS}' rsync -avz -e 'ssh -o StrictHostKeyChecking=no' {LOCAL_MEMORY_PATH} {VPS_USER}@{VPS_IP}:{VPS_TARGET_DIR}/"
        subprocess.run(rsync_cmd, shell=True, check=True, stdout=subprocess.DEVNULL)

        # 3. VPS Chattr Lock
        lock_cmd = f"sshpass -p '{SSH_PASS}' ssh -o StrictHostKeyChecking=no {VPS_USER}@{VPS_IP} 'sudo -n chattr +a {VPS_TARGET_DIR}/agent_memory.jsonl || true'"
        subprocess.run(lock_cmd, shell=True, stderr=subprocess.DEVNULL)

        logging.info("Sikeres szinkronizáció a VPS-re.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Hiba rsync szinkronizáció közben: {e}")

if __name__ == '__main__':
    print("Indítom a Helyi Memória Szinkronizáló Szolgáltatást (5 percenként)...")
    sync_memory()
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_memory, 'interval', minutes=5)
    scheduler.start()

    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
