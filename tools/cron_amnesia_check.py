import os
import sys
import subprocess

def add_cron_job():
    script_path = os.path.abspath("restore_env_ica.py")
    cron_cmd = f"0 * * * * cd {os.path.dirname(script_path)} && python3 {script_path} >> /tmp/jules_ica_cron.log 2>&1"

    try:
        # Lekérjük a jelenlegi crontab-ot
        current_cron = subprocess.check_output("crontab -l", shell=True, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        current_cron = ""

    if "restore_env_ica.py" not in current_cron:
        new_cron = current_cron + "\n" + cron_cmd + "\n"
        with open("/tmp/new_cron", "w") as f:
            f.write(new_cron)
        subprocess.run("crontab /tmp/new_cron", shell=True, check=True)
        os.remove("/tmp/new_cron")
        print("✅ Amnézia elleni cron job sikeresen hozzáadva: minden órában lefut a restore_env_ica.py")
    else:
        print("✅ Az amnézia elleni cron job már létezik.")

if __name__ == "__main__":
    add_cron_job()
