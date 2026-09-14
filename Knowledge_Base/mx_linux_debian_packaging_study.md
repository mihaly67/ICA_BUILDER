# MX Linux Debian Packaging Tanulmány (GUI Alkalmazásokhoz)

Ez a dokumentum rögzíti a sikeres \`.deb\` csomagolási struktúrát, miután a korábbi csomagok eltávolítása \`dpkg --configure -a\` fagyásokhoz vezetett a \`set -e\` és a Synaptic csomagkezelő összeférhetetlensége miatt. Továbbá megoldja a Synapticban megjelenő dupla kattintásos eltávolítási hibát (üres méret miatt).

## 1. A Probléma Gyökere (Dpkg megszakadt hiba)
MX Linux alatt a grafikus telepítők (mx-packageinstaller, Synaptic) egy \`pseudo-TTY\` környezetből hívják meg az \`apt-get purge\` vagy \`dpkg -i\` parancsokat.
* Ha a Debian csomagoló maintainer fájlok (\`postinst\`, \`prerm\`, \`postrm\`) tartalmaznak bármilyen manuális asztal frissítést (\`update-desktop-database\` vagy \`update-menus\`), a csomagkezelő GUI lefagyhat, lockolva a \`/var/lib/dpkg/lock-frontend\`-et.
* Ha nincs megadva \`Installed-Size\` a \`control\` fájlban, a Synaptic furcsán viselkedik (dupla kattintás nem működik az eltávolításhoz).

## 2. A Golyóálló Megoldás
Minden maintainer scriptnek követnie kell az alábbi szabályokat:
1.  **NE használj \`set -e\`-t** a fejlécben!
2.  A \`postinst\` és \`postrm\` szkripteknek **TELJESEN ÜRESNEK** kell lenniük (csak \`exit 0\`). Ne frissítsd a menüt kézzel, a dpkg trigger megcsinálja!
3.  **SOHA NE használj \`pkill -f <app_name>\`** parancsot, ha a \`<app_name>\` megegyezik a csomag nevével! Például \`pkill -f mx-ssh-monitor\` kilövi magát a \`dpkg\` folyamatot is eltávolításkor, ami szintén megszakadást okoz! Célozd közvetlenül a \`.py\` fájlt.
4.  A \`DEBIAN/control\` fájlba kötelező betenni az \`Installed-Size: <méret_KB>\` attribútumot!

## 3. MX Linux Ikonkezelés és Tálca (System Tray) szabályok
Amikor egy PyQt5 GUI alkalmazásnak egységes (KDE/Oxygen stílusú) ikont szeretnénk beállítani MX Linux alatt:
1. Az ikont szigorúan a rendszer gyári útvonaláról (pl. \`/usr/share/icons/oxygen/base/128x128/status/security-high.png\`) kell beolvasni abszolút útvonal megadásával, fallback-ként használva a \`QIcon.fromTheme("security-high")\` metódust.
2. Ezt a teljes abszolút útvonalat **egységesen** kell használni a \`.desktop\` fájl \`Icon=\` mezőjében, a PyQt5 \`setWindowIcon()\`-jában, és (ha van) a \`QSystemTrayIcon\`-ban is. Így az ablak és az asztali/menü parancsikon garantáltan ugyanaz lesz.
3. Ha egy alkalmazás **NEM automatikusan induló** (mint pl. a CPU Stress Test), de futtatás közben szeretnénk ha minimalizálva ne foglaljon helyet a feladatsávon: Akkor implementáljuk a \`QSystemTrayIcon\`-t. Viszont **semmiképp ne** másoljuk be a \`.desktop\` fájlt a \`~/.config/autostart/\` vagy \`/etc/xdg/autostart/\` mappákba!
4. Ha viszont **automatikusan induló** (mint pl. az SSH Monitor vagy a CyberSec Dashboard), akkor be kell állítani a System Tray ikont, és a \`.desktop\` fájlt is a \`/usr/share/applications/\` mellett be kell másolni az \`/etc/xdg/autostart/\` mappába a csomagolás során.

## 4. A Tökéletes Maintainer Scriptek (Sablon)

**\`DEBIAN/control\` (Részlet)**
\`\`\`text
Package: mx-ssh-monitor
Version: 1.1.3
Architecture: all
Installed-Size: 50
Depends: python3, python3-pyqt5, tailscale
...
\`\`\`

**\`DEBIAN/prerm\`**
\`\`\`bash
#!/bin/sh
pkill -f ssh_tailscale_monitor.py || true
exit 0
\`\`\`

**\`DEBIAN/postinst\` & \`DEBIAN/postrm\`**
\`\`\`bash
#!/bin/sh
exit 0
\`\`\`

## 5. Beragadt csomag kézi eltávolítása (GUI Lock eltávolítása)
Ha megtörtént a baj és a csomagkezelő "Waiting for cache lock" hibát dob folyamatosan (held by process X):
\`\`\`bash
# 1. Lődd ki a beragadt folyamatokat
sudo pkill -9 -f synaptic || true
sudo pkill -9 -f apt || true
sudo pkill -9 -f dpkg || true

# 2. Töröld a lock fájlokat
sudo rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock /var/lib/dpkg/lock-frontend

# 3. Kényszerített törlés
sudo dpkg --purge --force-all <hibas_csomag>
sudo rm -f /usr/share/applications/<alkalmazas_desktop_fajl>.desktop

# 4. Állapot helyreállítása
sudo dpkg --configure -a
\`\`\`
Ezután az új generációjú, javított \`.deb\` csomag sikeresen feltelepíthető a \`sudo dpkg -i\` paranccsal.
