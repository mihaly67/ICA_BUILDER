# Architecture Decision Record: Secure CI/CD & Observability

## Context
Három külső LLM auditor (Claude, Mistral, ChatGPT) megállapította, hogy a jelenlegi telepítési, megszakítási és monitorozási folyamatok "hazudnak", kiskapukat tartalmaznak (pl. `sshpass` text-alapú jelszóval, nyílt SSH tunneling, shell-injection sebezhetőség a monitorban), és megkerülik az `AGENTS_ICA.md` biztonsági előírásait (Zero Trust). A cél ezeknek a biztonsági réseknek a maradéktalan bezárása a helyi sandboxban, mielőtt élesben a VPS-re kerülnének.

## Decision
1. **Biztonságos CI/CD (deploy_to_vps.sh):**
   - **Tilos az `sshpass` használata!** A jelszavas hitelesítést teljes mértékben felváltja az SSH Public/Private kulcs alapú hitelesítés (`~/.ssh/id_rsa`).
   - A scriptnek szigorúan ellenőriznie kell az SSH kapcsolat meglétét jelszó kérése nélkül (pl. `ssh -o BatchMode=yes`).
   - Szigorú hibaellenőrzés: ha bármelyik lépés (pl. backup) hibára fut, a script azonnal leáll (`set -e`).
   - Nem másolunk nyersen mindent; csak a dedikált terjesztési csomagot mozgatjuk `rsync`-kel vagy szűrt `scp`-vel.

2. **Biztonságos Kill Switch (kill_vps_connection.sh):**
   - Az eddigi szkript, ami csak `pkill`-t használt egy `sshpass` nevű dologra, értelmetlen.
   - Az új Kill Switch megszakítja a lokális SSH agent-et (`ssh-add -D`), bezár minden meglévő SSH socket-et (`~/.ssh/sockets/`), és iptables/ufw szabállyal blokkolja a kimenő forgalmat a VPS IP-címe felé, ezáltal fizikailag, azonnal levágva az összeköttetést.

3. **Monitor Transzparencia (ica_web_monitor.py):**
   - **Tilos a `shell=True` használata** a `subprocess` hívásoknál (Command Injection sebezhetőség).
   - Python natív könyvtárakat (`psutil`) használunk a hardver metrikák lekérdezésére a `subprocess` hívások helyett (vagy ha muszáj awk-t, szigorú shell-mentes listákban futtatjuk).
   - A Guardrails státusz és a System Health nem rejtheti el a hibákat; ha a SQLite lekérdezés elbukik, a StackTrace-t (vagy tiszta hiba-objektumot) transzparensen továbbítjuk a frontendnek, nem írjuk felül "Nincs adat"-tal.

## Consequences
- A rendszer telepítése egy SSH kulcspár generálását és a VPS-en történő elhelyezését követeli meg (`ssh-copy-id`), ami megszünteti a jelszavak környezeti változókban való tartását.
- A `psutil` dependenciát hozzá kell adni a követelményekhez a monitor futtatásához.
- A Kill Switch valóban levágja az internetes hozzáférést a VPS irányába, biztosítva, hogy az agent nem tud visszajelentkezni véletlenül sem, ha a vészhelyzet fennáll.

## Status
Jóváhagyva és implementációra kész.
