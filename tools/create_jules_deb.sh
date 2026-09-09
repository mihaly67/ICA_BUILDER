#!/bin/bash
# Ez egy teljeskörű program a Jules (PyQt5) Security Center alkalmazások szabványos Debian (.deb) csomaggá alakítására.

APP_NAME="jules-security-center"
VERSION="1.0"
MAINTAINER="Jules AI <ai@jules.local>"

# A forráskód helye (a memóriában korábban jelzett útvonal a fizikai gépen)
SRC_DIR="/home/Jules/SecurityCenter_dev"

if [ ! -d "$SRC_DIR" ]; then
    echo "❌ Hiba: A forráskönyvtár ($SRC_DIR) nem található. Kérlek, állítsd be a helyes utat a scriptben."
    # Ezzel elkerüljük a session blokkolást a bash-ben
    # return 1
fi

if [ -d "$SRC_DIR" ]; then
    echo "[*] Debian csomag felépítésének megkezdése..."

    # Könyvtárstruktúra létrehozása a csomagoláshoz
    PKG_DIR="${APP_NAME}_${VERSION}"
    mkdir -p "${PKG_DIR}/opt/${APP_NAME}"
    mkdir -p "${PKG_DIR}/usr/share/applications"
    mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/128x128/apps"
    mkdir -p "${PKG_DIR}/DEBIAN"

    # Control fájl generálása
    cat << CONTROL > "${PKG_DIR}/DEBIAN/control"
Package: ${APP_NAME}
Version: ${VERSION}
Architecture: all
Maintainer: ${MAINTAINER}
Depends: python3, python3-pyqt5
Description: Jules Security Center and System Monitor
 A PyQt5 based GUI for monitoring ClamAV, Fail2ban and System hardware.
 Installed into /opt to ensure mx-snapshot includes it in the Live ISO.
CONTROL

    # Fájlok másolása
    echo "[*] Forráskód és ikonok átmásolása..."
    cp -r "${SRC_DIR}/"* "${PKG_DIR}/opt/${APP_NAME}/"

    # Jogosultságok beállítása a futtatható állományokra
    chmod +x "${PKG_DIR}/opt/${APP_NAME}/security_dashboard.py"
    if [ -f "${PKG_DIR}/opt/${APP_NAME}/start_cybersec.sh" ]; then
        chmod +x "${PKG_DIR}/opt/${APP_NAME}/start_cybersec.sh"
        EXEC_CMD="/opt/${APP_NAME}/start_cybersec.sh"
    else
        EXEC_CMD="python3 /opt/${APP_NAME}/security_dashboard.py"
    fi

    # Ha van ikon, másoljuk be, különben egy alap MX ikont használunk a .desktop fájlhoz
    if [ -f "${PKG_DIR}/opt/${APP_NAME}/icon.png" ]; then
        cp "${PKG_DIR}/opt/${APP_NAME}/icon.png" "${PKG_DIR}/usr/share/icons/hicolor/128x128/apps/${APP_NAME}.png"
        ICON_NAME="${APP_NAME}"
    else
        ICON_NAME="security-high"
    fi

    # Desktop fájl generálása (KDE / MX Linux menühöz)
    cat << DESKTOP > "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop"
[Desktop Entry]
Name=Jules Security Center
Comment=Monitor ClamAV, Fail2ban and System
Exec=${EXEC_CMD}
Icon=${ICON_NAME}
Terminal=false
Type=Application
Categories=System;Monitor;Security;
DESKTOP

    # Csomagolás futtatása
    echo "[*] dpkg-deb csomagépítés indítása..."
    dpkg-deb --build "${PKG_DIR}"

    if [ -f "${PKG_DIR}.deb" ]; then
        echo "✅ Kész! A telepítő elkészült: ${PKG_DIR}.deb"
        echo "👉 Telepítheted a 'sudo dpkg -i ${PKG_DIR}.deb' paranccsal."
        # Opcionálisan kitakaríthatjuk a munka mappát
        rm -rf "${PKG_DIR}"
    else
        echo "❌ Hiba a dpkg-deb futtatása közben."
    fi
fi
