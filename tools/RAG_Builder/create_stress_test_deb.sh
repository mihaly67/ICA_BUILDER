#!/bin/bash
# Debian csomagoló a CPU Stress Tester alkalmazáshoz

APP_NAME="jules-cpu-stress-tester"
VERSION="1.1"
MAINTAINER="Jules AI <ai@jules.local>"

# Csomagkönyvtár létrehozása a szerveren/lokálisan
PKG_DIR="/tmp/${APP_NAME}_${VERSION}"
rm -rf "$PKG_DIR"
mkdir -p "${PKG_DIR}/opt/${APP_NAME}"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${PKG_DIR}/DEBIAN"

# Control fájl
cat << CONTROL > "${PKG_DIR}/DEBIAN/control"
Package: ${APP_NAME}
Version: ${VERSION}
Architecture: all
Maintainer: ${MAINTAINER}
Depends: python3, python3-pyqt5, python3-psutil
Description: MX CPU Stress Tester (KDE Edition)
 A PyQt5 based GUI for mprime to torture test CPUs and RAM.
 Installed into /opt to ensure mx-snapshot includes it in the Live ISO.
CONTROL

# Postinst (Telepítés utáni menüfrissítő szkript)
cat << 'POSTINST' > "${PKG_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e
if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database -q || true
fi
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
# Fontos: Ne legyen exit 0, mert zavarja a heredocot a tesztkörnyezetben. (A debian postinst alapból visszatér)
POSTINST
chmod 755 "${PKG_DIR}/DEBIAN/postinst"

# Postrm (Törlés utáni menüfrissítő szkript)
cat << 'POSTRM' > "${PKG_DIR}/DEBIAN/postrm"
#!/bin/sh
set -e
if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database -q || true
fi
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
POSTRM
chmod 755 "${PKG_DIR}/DEBIAN/postrm"

# Forráskód bemásolása
cp tools/RAG_Builder/cpu_stress_test.py "${PKG_DIR}/opt/${APP_NAME}/"
chmod +x "${PKG_DIR}/opt/${APP_NAME}/cpu_stress_test.py"

# Futtató wrapper script
cat << WRAPPER > "${PKG_DIR}/opt/${APP_NAME}/start_stress.sh"
#!/bin/bash
export DISPLAY=:0
if [ -f "/home/\$USER/.Xauthority" ]; then
    export XAUTHORITY="/home/\$USER/.Xauthority"
fi
python3 /opt/${APP_NAME}/cpu_stress_test.py
WRAPPER
chmod +x "${PKG_DIR}/opt/${APP_NAME}/start_stress.sh"

# Egyedi SVG Ikon generálása a CPU Stressz teszternek (kék-szürke dizájn)
cat << SVG_ICON > "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps/${APP_NAME}.svg"
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="12" fill="#31363b"/>
  <rect x="8" y="8" width="48" height="48" rx="8" fill="#232629" stroke="#3daee9" stroke-width="3"/>
  <path d="M20 20 h24 v24 h-24 z" fill="#3daee9"/>
  <path d="M12 16 h4 m32 0 h4 m-40 8 h4 m32 0 h4 m-40 8 h4 m32 0 h4 m-40 8 h4 m32 0 h4 M16 12 v4 m8 -4 v4 m8 -4 v4 m8 -4 v4 m-24 40 v-4 m8 4 v-4 m8 4 v-4 m8 4 v-4" stroke="#76797c" stroke-width="2"/>
  <circle cx="32" cy="32" r="6" fill="#da4453"/>
</svg>
SVG_ICON

# Desktop fájl (A "System" mellett betesszük az "MX-Setup" kategóriába is)
cat << DESKTOP > "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop"
[Desktop Entry]
Name=MX CPU Stress Tester
Comment=Hardware instability and thermal throttling diagnostic tool (mprime)
Exec=/opt/${APP_NAME}/start_stress.sh
Icon=${APP_NAME}
Terminal=false
Type=Application
Categories=System;MX-Setup;
DESKTOP

# Csomag építése a /tmp mappában
dpkg-deb --build "${PKG_DIR}"
