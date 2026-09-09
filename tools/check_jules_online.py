import subprocess
import time
import sys

TARGET_IP = "100.77.191.66"

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
    print("👉 A szkript most várakozik, amíg a gép újra online nem lesz (ellenőrzés 10 másodpercenként).")
    print("👉 Ha meg akarod szakítani a várakozást, nyomj Ctrl+C-t.\n")

    attempt = 1
    try:
        while True:
            time.sleep(10)
            if check_connection():
                print(f"\n✅ SIKER! A gép (Jules) online lett a {attempt}. próbálkozásra!")
                sys.exit(0)
            else:
                sys.stdout.write(f"\r⏳ Várakozás a gépre... (Próbálkozás: {attempt})")
                sys.stdout.flush()
                attempt += 1
    except KeyboardInterrupt:
        print("\n\n[!] Várakozás megszakítva a felhasználó által.")
        sys.exit(1)

if __name__ == "__main__":
    main()
