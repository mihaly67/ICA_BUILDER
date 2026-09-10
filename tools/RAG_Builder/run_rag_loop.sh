#!/bin/bash
# Ez a script folyamatosan újraindítja a vektorizálót, amíg az teljesen be nem fejeződik.
# Kikerüli a Python/SQLite memória és I/O szivárgását a hosszú futások során.

echo "[*] RAG Vektorizáló Wrapper indítása..."

export XAUTHORITY=/home/Jules/.Xauthority
export DISPLAY=:0

while true; do
    echo "[*] Vektorizáló folyamat indítása..."

    # Python script futtatása a virtuális környezetből
    /home/Jules/jules_venv/bin/python3 /home/Jules/MX_LINUX_RAG/build_rag_cuda.py

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "[*] Vektorizálás befejeződött vagy megszakították (Sikeres kilépés)."
        break
    elif [ $EXIT_CODE -eq 42 ]; then
        echo "[*] Chunk limit elérve. Memória felszabadítása és azonnali újraindítás..."
        # Pici szünet, hogy az OS kidobja a cache-eket
        sleep 1
    else
        echo "[!] Váratlan hiba történt (Exit kód: $EXIT_CODE). Újraindítás 5 másodperc múlva..."
        sleep 5
    fi
done

echo "[*] RAG Vektorizáló Wrapper leállt."
