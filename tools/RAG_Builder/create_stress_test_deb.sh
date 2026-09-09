#!/bin/bash
# Debian csomagoló a CPU Stress Tester alkalmazáshoz

APP_NAME="jules-cpu-stress-tester"
VERSION="1.0"
MAINTAINER="Jules AI <ai@jules.local>"

# Csomagkönyvtár létrehozása a szerveren/lokálisan
PKG_DIR="/tmp/${APP_NAME}_${VERSION}"
rm -rf "$PKG_DIR"
mkdir -p "${PKG_DIR}/opt/${APP_NAME}"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/DEBIAN"

# Control fájl
# Code Review javítás: A python3-psutil visszakerült, mert standard debian csomag
# és a PyQt script elszállna import errorral. Csak a külső 'mprime' lett kivéve!
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

# Forráskód bemásolása
cp tools/RAG_Builder/cpu_stress_test.py "${PKG_DIR}/opt/${APP_NAME}/"
chmod +x "${PKG_DIR}/opt/${APP_NAME}/cpu_stress_test.py"

# Futtató wrapper script a megfelelő környezeti változók exportálásához
cat << WRAPPER > "${PKG_DIR}/opt/${APP_NAME}/start_stress.sh"
#!/bin/bash
export DISPLAY=:0
# MX Linux KDE speciális X11 envs:
if [ -f "/home/\$USER/.Xauthority" ]; then
    export XAUTHORITY="/home/\$USER/.Xauthority"
fi
python3 /opt/${APP_NAME}/cpu_stress_test.py
WRAPPER
chmod +x "${PKG_DIR}/opt/${APP_NAME}/start_stress.sh"

# Desktop fájl (KDE / MX Linux menühöz)
cat << DESKTOP > "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop"
[Desktop Entry]
Name=MX CPU Stress Tester
Comment=Hardware instability and thermal throttling diagnostic tool (mprime)
Exec=/opt/${APP_NAME}/start_stress.sh
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=System;Monitor;HardwareSettings;
DESKTOP

# Csomag építése a /tmp mappában
dpkg-deb --build "${PKG_DIR}"
