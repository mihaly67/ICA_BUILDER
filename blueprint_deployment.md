# Architecture Decision Record: Secure CI/CD & Observability

## Context
Három külső LLM auditor (Claude, Mistral, ChatGPT) megállapította, hogy a jelenlegi telepítési, megszakítási és monitorozási folyamatok "hazudnak", kiskapukat tartalmaznak (pl. `sshpass` text-alapú jelszóval, nyílt SSH tunneling, shell-injection sebezhetőség a monitorban), és megkerülik az `AGENTS_ICA.md` biztonsági előírásait (Zero Trust). A cél ezeknek a biztonsági réseknek a maradéktalan bezárása a helyi sandboxban, mielőtt élesben a VPS-re kerülnének.

## Decision

1. **Biztonságos CI/CD (deploy_to_vps.sh):**
   - **Tilos az `sshpass` használata!** SSH Public/Private kulcs használata kötelező.
   - Szigorú hibaellenőrzés: `set -e` használata, **kiegészítve egy `trap` mechanizmussal** (rollback/cleanup), hogy hiba esetén a rendszer ne maradjon inkonzisztens "félkész" állapotban. Külön figyelmet kell fordítani a fájl-alapú műveletekre, például a kezdeti könyvtárak biztonsági mentésére (`if [ -d ... ]`).
   - Szigorú `rsync` szűrés: kiterjedt `--exclude` paraméterek (pl. `.git`, `.env`, lokális `.db`, `.log` fájlok) használata kötelező a lokális szemét VPS-re kerülésének elkerülése végett.

2. **Biztonságos Kill Switch & Revive (kill_vps_connection.sh & restore_vps_connection.sh):**
   - A Kill Switch megszakítja a lokális SSH agent-et, bezár minden socket-et, és iptables/ufw szabállyal blokkolja a VPS felé a forgalmat.
   - **Sudo jogosultság:** A szkript dokumentálja a szükséges `NOPASSWD` sudo beállításokat az agent számára, így vészhelyzetben a terminál nem akad meg jelszókérésen.
   - **Revive terv:** Létrejön egy `restore_vps_connection.sh` szkript, ami az iptables/ufw szabályokat visszavonja a hálózat helyreállítása érdekében.

3. **Monitor Transzparencia & Információvédelem (ica_web_monitor.py):**
   - **Tilos a `shell=True` használata** a `subprocess` hívásoknál (psutil használata).
   - **Information Disclosure védelem:** A nyers StackTrace sosem kerül ki a frontend felé. Ehelyett a backend naplózza a részletes hibát, a frontend pedig egy egyedi Correlation ID-t kap ("Adatbázis hiba történt. ID: Err-XYZ"). Ez a megoldás egyszerre őszinte (nem hallgatja el a hibát) és biztonságos (nem szivárogtat rendszerszintű adatokat).

## Consequences
- A `deploy_to_vps.sh` hiba esetén mostantól tiszta állapotot hagy (vagy egyértelmű hibaüzenetet) a `trap` használatával.
- A felhasználónak (misi/jules) sudo jogokat kell konfigurálnia a Kill Switch hálózati szintű végrehajtásához (`visudo`).
- A Monitor backend naplóját folyamatosan vizsgálni kell a Correlation ID-k alapján az elrejtett kivételek okainak feltárásához.

## Status
Jóváhagyva és implementációra kész.
