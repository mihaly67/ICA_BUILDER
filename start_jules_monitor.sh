#!/bin/bash
# Local SSH tunnel script
# Ensure we have absolute paths or explicitly change directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Indítom az SSH Tunnelt a Jules VPS felé (Port 8080)..."
sshpass -p "$VPS_PWD" ssh -N -L 8080:localhost:8080 misi@$VPS_HOST -o StrictHostKeyChecking=no &
SSH_PID=$!

sleep 2
echo "Megnyitom a böngészőt..."
xdg-open http://127.0.0.1:8080

echo "A monitor fut. Nyomj CTRL+C-t a leállításhoz."
wait $SSH_PID
