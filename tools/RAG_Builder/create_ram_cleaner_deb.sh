#!/bin/bash
APP_NAME="jules-ram-cleaner"
VERSION="1.0"
MAINTAINER="Jules AI <ai@jules.local>"

PKG_DIR="/tmp/${APP_NAME}_${VERSION}"
rm -rf "$PKG_DIR"
mkdir -p "${PKG_DIR}/opt/${APP_NAME}"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${PKG_DIR}/DEBIAN"

cat << CONTROL > "${PKG_DIR}/DEBIAN/control"
Package: ${APP_NAME}
Version: ${VERSION}
Architecture: all
Maintainer: ${MAINTAINER}
Depends: python3, python3-pyqt5, python3-psutil, policykit-1
Description: MX RAM and Cache Cleaner (KDE Edition)
 A PyQt5 GUI tool to monitor and drop Linux system caches and swap.
 Installed into /opt to ensure mx-snapshot includes it in the Live ISO.
CONTROL

cat << 'POSTINST' > "${PKG_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e
if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database -q || true
fi
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
POSTINST
echo "exit 0" >> "${PKG_DIR}/DEBIAN/postinst"
chmod 755 "${PKG_DIR}/DEBIAN/postinst"

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
echo "exit 0" >> "${PKG_DIR}/DEBIAN/postrm"
chmod 755 "${PKG_DIR}/DEBIAN/postrm"

cp tools/RAG_Builder/ram_cache_cleaner.py "${PKG_DIR}/opt/${APP_NAME}/"
chmod +x "${PKG_DIR}/opt/${APP_NAME}/ram_cache_cleaner.py"

cat << WRAPPER > "${PKG_DIR}/opt/${APP_NAME}/start_cleaner.sh"
#!/bin/bash
export DISPLAY=:0
if [ -f "/home/\$USER/.Xauthority" ]; then
    export XAUTHORITY="/home/\$USER/.Xauthority"
fi
python3 /opt/${APP_NAME}/ram_cache_cleaner.py
WRAPPER
chmod +x "${PKG_DIR}/opt/${APP_NAME}/start_cleaner.sh"

cat << SVG_ICON > "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps/${APP_NAME}.svg"
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="12" fill="#31363b"/>
  <rect x="8" y="24" width="48" height="16" rx="4" fill="#232629" stroke="#da4453" stroke-width="3"/>
  <rect x="12" y="28" width="8" height="8" fill="#da4453"/>
  <rect x="24" y="28" width="8" height="8" fill="#da4453"/>
  <rect x="36" y="28" width="8" height="8" fill="#da4453"/>
  <path d="M16 16 l8 -8 l8 8 m-8 -8 v16 m16 24 l8 8 l8 -8 m-8 8 v-16" stroke="#3daee9" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
SVG_ICON

cat << DESKTOP > "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop"
[Desktop Entry]
Name=MX RAM & Cache Cleaner
Comment=Monitor and free up system memory and file cache
Exec=/opt/${APP_NAME}/start_cleaner.sh
Icon=${APP_NAME}
Terminal=false
Type=Application
Categories=System;MX-Setup;
DESKTOP

dpkg-deb --build "${PKG_DIR}"
