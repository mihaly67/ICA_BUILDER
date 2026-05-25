# 🛡️ JULES ICA: ZERO TRUST RENDSZER HASZNÁLATI ÚTMUTATÓ (GUIDE)

Mivel a rendszerünk átállt egy szigorú Zero Trust (Nulla Bizalom) alapú, professzionális architektúrára, a jövőbeli biztonságos és stabil együttműködéshez az alábbi munkamegosztás szükséges.

Ez a dokumentum pontosan leírja, **mit kell tenned Neked** (Mint rendszergazda/üzemeltető), és **mit fogok tenni Én** (Mint az ICA rendszerépítő Agent).

---

## 🧑‍💻 A TE TEENDŐID (Felhasználó / Misi)

Az új biztonsági szkriptek (`deploy_to_vps.sh`, `kill_vps_connection.sh`) lokálisan elkészültek a Sandboxban, de ahhoz, hogy élesben is működjenek a gépeden (és megvédjenek minket), az alábbi egyszeri beállításokat el kell végezned a lokális Linux (MX Linux) rendszereden:

### 1. SSH Kulcs Alapú Hitelesítés (Jelszómentesség beállítása)
Az `sshpass` (nyílt szöveges jelszó) örökre kikerült a rendszerből. Helyette SSH kulcsot kell használni.
Nyiss egy terminált a **lokális gépeden**, és futtasd le ezt:
```bash
# Ha még nincs kulcsod (ha van, ezt a lépést átugorhatod):
ssh-keygen -t ed25519 -C "jules_ica_deploy"

# A kulcs átmásolása a VPS-re:
ssh-copy-id misi@5.189.163.88
```
*Próbáld ki: Az `ssh misi@5.189.163.88` parancsnak ezután jelszó kérése nélkül be kell engednie.*

### 2. A Kill Switch Jogosultságainak Beállítása (Sudoers)
Hogy a Vészleállító Gomb (Kill Switch) ne akadjon meg a sudo jelszó kérésén, engedélyezned kell a hálózati parancsok jelszó nélküli futtatását a gépeden.
Nyisd meg a visudo-t a **lokális gépeden**:
```bash
sudo visudo
```
Másold be a fájl végére ezt a blokkot (ellenőrizd az iptables elérési útját a `which iptables` paranccsal, de általában ez megfelelő):
```text
misi ALL=(ALL) NOPASSWD: /usr/sbin/iptables -w -I OUTPUT -d 5.189.163.88 -j REJECT
misi ALL=(ALL) NOPASSWD: /usr/sbin/iptables -w -D OUTPUT -d 5.189.163.88 -j REJECT
misi ALL=(ALL) NOPASSWD: /usr/sbin/iptables -w -I INPUT -s 5.189.163.88 -j DROP
misi ALL=(ALL) NOPASSWD: /usr/sbin/iptables -w -D INPUT -s 5.189.163.88 -j DROP
misi ALL=(ALL) NOPASSWD: /usr/sbin/ufw deny out to 5.189.163.88
misi ALL=(ALL) NOPASSWD: /usr/sbin/ufw delete deny out to 5.189.163.88
misi ALL=(ALL) NOPASSWD: /usr/sbin/ufw deny from 5.189.163.88
misi ALL=(ALL) NOPASSWD: /usr/sbin/ufw delete deny from 5.189.163.88
misi ALL=(ALL) NOPASSWD: /usr/bin/umount -l /home/misi/Jules_ICA_Builder_Remote
misi ALL=(ALL) NOPASSWD: /usr/bin/chattr
```
*A chattr az append-only log fájlok (Tamper-Proofing) miatt szükséges.*
*Mentsd el a fájlt (nano esetén: `Ctrl+O`, `Enter`, `Ctrl+X`).*

### 3. Az Élesítés
Ha az előző két pont megvan, nyisd meg a lokális terminált a `Jules_ICA_Builder` mappában, és küldd fel a csomagot a VPS-re:
```bash
./deploy_to_vps.sh
```
Ez a parancs biztonságosan, rsync-kel felmásolja az új, jelszómentes, psutil-t használó kódbázist a szerverre, majd újraindítja a Web Monitort és a Routert.

### 4. Parancsikonok a Desktopon (Opcionális, de ajánlott)
Húzd ki a `kill_vps_connection.sh` és a `restore_vps_connection.sh` fájlokat az asztalodra, vagy csinálj hozzájuk gyorsindítót, hogy egy dupla kattintással azonnal levághasd a VPS-t hiba esetén.

---

## 🤖 AZ ÉN TEENDŐIM (Jules / Agent)

Mostantól, hogy a biztonságos csatorna kiépült, az én viselkedésem és feladatom a következő az AGENTS_ICA.md és a System 2 protokoll alapján:

### 1. Nincs több SSH "Hackelés" és Patch
* Ezentúl **Szigorúan Tilos** a VPS-re direktbe belépve Python kódokat vagy patch fájlokat írnom. Minden fejlesztést itt, a **lokális repódban (Sandbox)** fogok megcsinálni és letesztelni.
* Csak miután helyben (Nálad) mindent rendben találtam, kérem a jóváhagyásodat, vagy futtatom le az általunk írt `deploy_to_vps.sh` szkriptet a kód élesítéséhez.

### 2. Szigorú "Design Before Coding" (Kognitív Pipeline)
Bármilyen új funkciót vagy modult is kérsz tőlem a jövőben:
* **Először** megnézem a meglévő RAG tudásbázisunkat.
* **Másodszor** megírom/frissítem a `blueprint.md` (ADR) fájlt. Csak ha a terv hibátlan és egyetértünk benne,
* **Harmadszor** fogok csak kódot generálni, a szintaktikai validáló (Guardrails) engedélyével.

### 3. Memória és Tudásgráf Karbantartása
* Folyamatosan frissítem az `agent_memory.jsonl`-t (Önreflexióval, ahogy az Auditorok kérték).
* Szinkronban tartom a lokális állapotokat a szerver állapotával, úgy, hogy sosem írom felül a tudásbázist hibás adatokkal, és ha hiba történik a Web Monitorban, azt tiszta `Correlation ID` (Err-XYZ) alapon mutatom meg a képernyőn, megvédve a szerver adatait a szivárgástól.

---
**Röviden:** Neked csak az SSH hitelesítést és a Sudoers kivételeket kell beállítanod a gépeden, majd lefuttatni a `deploy_to_vps.sh`-t. Utána hátradőlhetsz, és oszthatod az új fejlesztési feladatokat a lokális Sandboxomba!
