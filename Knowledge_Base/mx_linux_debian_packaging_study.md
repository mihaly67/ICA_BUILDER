# MX Linux Debian Packaging Tanulmány (GUI Alkalmazásokhoz)

Ez a dokumentum rögzíti a sikeres \`.deb\` csomagolási struktúrát, miután a korábbi csomagok eltávolítása \`dpkg --configure -a\` fagyásokhoz vezetett a \`set -e\` és a Synaptic csomagkezelő összeférhetetlensége miatt.

## 1. A Probléma Gyökere (Dpkg megszakadt hiba)
MX Linux alatt a grafikus telepítők (mx-packageinstaller) egy \`pseudo-TTY\` környezetből hívják meg az \`apt-get purge\` vagy \`dpkg -i\` parancsokat. Ha a Debian csomagoló maintainer fájlok (\`postinst\`, \`prerm\`, \`postrm\`) fejléce tartalmazza a **\`set -e\`** (exit on error) kapcsolót, és egy parancs hibával tér vissza (pl. nincs feltelepítve az \`update-desktop-database\`), a folyamat megszakad.
Ezután a csomag félig-telepített/félig-törölt (inconsistent) állapotban ragad a rendszerben, ami megbénítja a csomagkezelőt.

## 2. A Golyóálló Megoldás
Minden maintainer scriptnek követnie kell az alábbi szabályokat:
1.  **NE használj \`set -e\`-t** a fejlécben!
2.  Minden futtatott parancs végére tegyél **\`|| true\`** feltételt.
3.  A binárisokat a teljes elérési úttal ellenőrizd (pl. \`[ -x /usr/bin/update-desktop-database ]\`).
4.  **SOHA NE használj \`pkill -f <app_name>\`** parancsot, ha a \`<app_name>\` megegyezik a csomag nevével! Például \`pkill -f mx-ssh-monitor\` kilövi magát a \`dpkg\` folyamatot is eltávolításkor, ami szintén megszakadást okoz! Célozd közvetlenül a \`.py\` fájlt.

## 3. A Tökéletes Maintainer Scriptek (Sablon)

**\`DEBIAN/prerm\`**
\`\`\`bash
#!/bin/sh
pkill -f ssh_tailscale_monitor || true
exit 0
\`\`\`

**\`DEBIAN/postinst\` & \`DEBIAN/postrm\`**
\`\`\`bash
#!/bin/sh
if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database -q || true
fi
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
if command -v update-menus >/dev/null 2>&1; then
    update-menus || true
fi
exit 0
\`\`\`

## 4. Beragadt csomag kézi eltávolítása
Ha megtörtént a baj, a következő parancsokkal takarítsd ki a rendszert:
\`\`\`bash
sudo rm -f /var/lib/dpkg/info/<hibas_csomag>.*
sudo dpkg --purge --force-all <hibas_csomag>
sudo dpkg --configure -a
\`\`\`
Ezután az új generációjú, javított \`.deb\` csomag sikeresen feltelepíthető a \`sudo dpkg -i\` paranccsal.
exit 0
