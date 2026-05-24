# Lokális Fejlesztési és Távoli Telepítési Terv (CI/CD)

Mivel a közvetlen "SSH hekkelés" a szerveren hibákhoz és szinkronizálatlan fájlokhoz vezetett, az alábbi folyamatot dolgoztam ki, hogy a lokális Sandbox-ban (lemezen) tesztelt kódot biztonságosan juttassuk a VPS-re.

## 1. Lokális Tesztelés a Sandboxban (Fejlesztés)
A kódolás mindig a lokális `src/` és root könyvtárakban történik.
* Teszteljük, hogy a fájl szintaktikailag helyes-e (a Guardrails fut lokálisan).
* A változásokat kötelezően a lokális git repóban (sandbox) vezetjük át és kommitoljuk.

## 2. Biztonságos Telepítő Script Készítése (`deploy_to_vps.sh`)
Létrehozunk egy bash scriptet, aminek egyetlen feladata, hogy a lokális módosításokat feljuttassa a VPS-re, **de csakis biztonságos módon**.
Ez a script:
1. PING-eli az SSH kapcsolatot és teszteli az elérést.
2. Egy ideiglenes könyvtárba (`/tmp/jules_deploy`) másolja a fájlokat SCP-vel.
3. Készít egy automatikus biztonsági mentést a VPS jelenlegi fájljairól (`tar -czf backup_$(date).tar.gz /home/misi/Jules_ICA_Builder/`).
4. Lemásolja az új fájlokat a temp könyvtárból a végleges helyükre.
5. Újraindítja az érintett szolgáltatásokat (pkill mcp_router, ica_web_monitor start).

## 3. Vészhelyzeti "Kill Switch" (Kapcsolat Levágása)
Be kell állítanunk egy rendszert a felhasználó (misi) számára, amivel azonnal levághatja a VPS hozzáférést, ha elszabadul az AI vagy a kód:
* Létrehozunk egy `kill_vps_connection.sh` fájlt a lokális Desktopon (MX Linux / Sandbox).
* Ez a script azonnal módosítja/letiltja a SSH kulcsot, megöli a helyi SSH tunnelt (ha fut), és értesítést dob a sikeres leválasztásról. Ezt beállítjuk futtathatóként a te MX Linux asztalodon, így egy kattintással meg tudod ölni a folyamatot, és én (mint LLM) azonnal kizárom magam.

## Következő lépések a megvalósításig:
1. `deploy_to_vps.sh` megírása.
2. `kill_vps_connection.sh` megírása és kihelyezése.
3. Git Commit (Blueprint/Terv rögzítése).
