# XRDP és GUI Hibaelhárítási Útmutató (Jules ICA VPS)

Ez a dokumentum a távoli asztali (RDP) kapcsolatokkal, az Ubuntu 24.04+ rendszerekkel és a Jules ICA Monitor grafikus felületével kapcsolatos ismert anomáliákat és azok megoldásait tartalmazza. Különösen hasznos, ha a felhasználó okostelefonról vagy tisztán parancssorból (SSH) próbálja helyreállítani a grafikus munkamenetet.

## 1. A "Sötét / Fekete Képernyő" Hiba (XRDP + XFCE4)

### A probléma oka
Amikor a Remmina (vagy más RDP kliens) megszakad, az XFCE asztali környezet és az X11 szerver a háttérben "zombiként" nyitva maradhat. Amikor a felhasználó újra csatlakozik, az XRDP nem tudja felülírni vagy átvenni ezt a befagyott DBUS/X11 munkamenetet, így a képernyő fekete marad. Ubuntu 24.04 alatt a probléma hatványozott a hiányzó `dbus-x11` és az elavult `.xsession` konfigurációk miatt.

### Megoldás parancssorból (SSH)
Ha fekete képernyőt kapsz, lépj be a VPS-re SSH-n keresztül, és futtasd az alábbi parancsokat a beragadt folyamatok kilövéséhez és az RDP újraindításához:

```bash
# 1. Zombi folyamatok azonnali kilövése (Fekete képernyő feloldása)
sudo killall -9 xfce4-session Xorg xrdp xrdp-sesman xrdp-chansrv dbus-launch xfce4-panel 2>/dev/null

# 2. Beragadt X11 munkameneti fájlok törlése
rm -f ~/.Xauthority
rm -f ~/.xsession-errors

# 3. Biztosítsuk a helyes, Systemd-kompatibilis .xsession fájlt
cat << 'IN' > ~/.xsession
#!/bin/bash
export XDG_SESSION_DESKTOP=xfce
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=XFCE
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
exec dbus-launch --exit-with-session xfce4-session
IN
chmod +x ~/.xsession

# 4. XRDP Szolgáltatások újraindítása
sudo systemctl restart xrdp xrdp-sesman
```
*Tipp:* Ezeket a parancsokat a VPS asztalán lévő `XRDP_Fix.desktop` és a `xrdp_fix_and_restart.sh` script is tartalmazza.

---

## 2. A "Snap" Böngésző Probléma (Firefox vs. Chrome)

### A probléma oka
Ha a Jules Web Monitor Dashboardját próbálod megnyitni az RDP munkamenetből az alapértelmezett böngészővel (általában Firefox), előfordulhat, hogy a böngésző egyáltalán nem nyílik meg, vagy hibaüzenetet ad a System Monitorban (`system.slice/xrdp-sesman.service is not a snap cgroup`).

Modern Ubuntu rendszereken a Firefox tisztán **Snap csomagként** létezik. A Snap rendkívül szigorú AppArmor és cgroup jogosultságokat követel meg. Mivel a távoli XRDP munkamenet nem a fő fizikai Systemd környezetben (`user.slice`), hanem az XRDP alrendszerében (`system.slice`) indul, az Ubuntu egyszerűen **megtagadja a Snap böngészők elindítását** biztonsági okokra hivatkozva.

### Az ICA Hivatalos Megoldása (Google Chrome)
Soha ne használj Snap-alapú böngészőt az XRDP környezetben. A megoldás a **natív `.deb` csomagból telepített Google Chrome** használata. Ezt az ICA asztali indítóikonjai is automatikusan kikényszerítik az alábbi parancsstruktúrával:

```bash
# Helyes böngésző indítás a Web Monitorhoz XRDP alatt, elrejtve a felesleges terminál hibaüzeneteket:
google-chrome --no-sandbox http://127.0.0.1:8080 > /dev/null 2>&1
```

*Ha nincs Chrome a szerveren, a következő paranccsal telepíthető:*
```bash
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install -y google-chrome-stable
```
