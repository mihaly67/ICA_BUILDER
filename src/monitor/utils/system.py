import os
import psutil
import shutil
import time
import logging
import uuid
import html

last_cpu_time = 0
last_cpu_percent = 0.0

def get_system_health():
    global last_cpu_time, last_cpu_percent
    current_time = time.time()
    try:
        if current_time - last_cpu_time > 1.0:
            last_cpu_percent = psutil.cpu_percent(interval=None)
            last_cpu_time = current_time

        cpu = f"{last_cpu_percent}%"
        mem_info = psutil.virtual_memory()
        mem = f"{mem_info.percent}%"
        disk_info = shutil.disk_usage("/")
        disk = f"{(disk_info.used / disk_info.total) * 100:.1f}%"
        return f"CPU Használat: {cpu}\nRAM Használat: {mem}\nLemez (/): {disk}"
    except Exception as e:
        err_id = str(uuid.uuid4())[:8]
        logging.error(f"Error [{err_id}] in System Health Check: {e}", exc_info=True)
        return f"Rendszerállapot lekérdezés sikertelen. ID: Err-{err_id}"

def get_swarm_inbox(inbox_dir="/home/misi/Jules_ICA_Builder/inbox"):
    inbox_str = ""
    try:
        if os.path.exists(inbox_dir):
            files = [f for f in os.listdir(inbox_dir) if f.startswith("msg_") and f.endswith(".txt")]
            if files:
                for f in files:
                    filepath = os.path.join(inbox_dir, f)
                    with open(filepath, 'r', encoding='utf-8') as file:
                        inbox_str += f"[{f}]: {html.escape(file.read()[:50])}...\n"
            else:
                inbox_str = "Nincsenek várakozó Swarm üzenetek."
        else:
            inbox_str = "Inbox könyvtár nem létezik."
    except Exception as e:
        inbox_str = f"Hiba az Inbox olvasásakor: {e}"
    return inbox_str
