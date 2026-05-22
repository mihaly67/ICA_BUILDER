#!/bin/bash
# Jules ICA Web Monitor Indító Szkript (SSH Tunnel)

VPS_HOST=${VPS_HOST:-"5.189.163.88"}
VPS_USER=${VPS_USER:-"misi"}
PORT="8080"

echo "🧠 Jules ICA Rendszerfelügyelet indítása..."
echo "🔗 Kapcsolódás a VPS-hez ($VPS_HOST) SSH tunnelen keresztül (Port: $PORT)..."

# Jelszó vagy kulcs alapú csatlakozás a háttérben
if [ -n "$VPS_PWD" ]; then
    if command -v sshpass &> /dev/null; then
        sshpass -p "$VPS_PWD" ssh -N -f -L $PORT:127.0.0.1:$PORT $VPS_USER@$VPS_HOST -o StrictHostKeyChecking=no
    else
        echo "Kérlek, telepítsd az sshpass-t: sudo apt install sshpass (vagy használd SSH kulcsot)"
        ssh -N -f -L $PORT:127.0.0.1:$PORT $VPS_USER@$VPS_HOST
    fi
else
    # Kulcsos bejelentkezés
    ssh -N -f -L $PORT:127.0.0.1:$PORT $VPS_USER@$VPS_HOST
fi

sleep 2

# Böngésző megnyitása
echo "🌐 Böngésző megnyitása: http://127.0.0.1:$PORT"
if command -v xdg-open &> /dev/null; then
    xdg-open "http://127.0.0.1:$PORT"
elif command -v open &> /dev/null; then
    open "http://127.0.0.1:$PORT"
fi

echo "✅ Kész!"
