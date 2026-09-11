import subprocess
import time
import sys

TARGET_IP = "100.77.191.66"
MAX_ATTEMPTS = 12 # 2 perc várakozás maximum (12 * 10mp)

def check_connection():
    """Visszaadja a True-t, ha a gép válaszol a pingre, különben False-t."""
    # Egyszerű ping 1 csomaggal, 2 másodperces timeouttal
    cmd = ["ping", "-c", "1", "-W", "2", TARGET_IP]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def main():
    print(f"[*] Kapcsolat ellenőrzése a fizikai Jules géppel ({TARGET_IP})...")

    if check_connection():
        print("✅ A gép ONLINE és elérhető a hálózaton!")
        sys.exit(0)

    print("❌ A gép jelenleg OFFLINE (kikapcsolva vagy nincs a Tailscale hálózaton).")
    print("\n👉 SEMMI PÁNIK! Kérlek, kapcsold be a fizikai gépet (Jules).")
    print(f"👉 A szkript most maximum {MAX_ATTEMPTS} alkalommal próbálkozik (10 másodpercenként).")
    print("👉 Ha meg akarod szakítani a várakozást, nyomj Ctrl+C-t.\n")

    attempt = 1
    try:
        while attempt <= MAX_ATTEMPTS:
            time.sleep(10)
            if check_connection():
                print(f"\n✅ SIKER! A gép (Jules) online lett a {attempt}. próbálkozásra!")
                sys.exit(0)
            else:
                sys.stdout.write(f"\r⏳ Várakozás a gépre... (Próbálkozás: {attempt}/{MAX_ATTEMPTS})")
                sys.stdout.flush()
                attempt += 1

        print("\n\n[!] Időtúllépés. A fizikai gép továbbra is offline.")
        print("[!] A környezet inicializálása folytatódik, de a fizikai gép funkciói nem lesznek elérhetőek.")
        # Ne lépjünk ki hibával, hogy a restore_env_ica.py tovább tudjon menni a VPS beállításokkal
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n[!] Várakozás megszakítva a felhasználó által.")
        sys.exit(0) # Itt is 0-val lépünk ki, hogy ne törjük meg a setupot

if __name__ == "__main__":
    main()
