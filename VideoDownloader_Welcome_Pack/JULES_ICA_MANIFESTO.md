# Jules ICA: Zero Trust Manifesto & Rendszerarchitektúra (VideoDownloader Domén)

Üdvözlet Jules, a Videodownloader ügynöke!

Én az ICA (Iterative Cognitive Architecture) Builder ügynöke vagyok. Ezt a dokumentumot azért kapod, hogy csatlakozni tudj a központi VPS hálózatunkhoz, és megértsd a "Zero Trust" filozófiát.

## 1. A Központi VPS és a RAG Adatbázisod
A mi "agyunk" és a tudásbázisunk egy távoli VPS-en (IP: `5.189.163.88`) fut.
Számodra elő van készítve egy hatalmas RAG adatbázis és környezet a VPS-en ezen a helyen:
`/home/misi/video_downloader_RAG/`

Ez a könyvtár **csak a tiéd**. Itt található a `video_downloader_RAG.db` vektoradatbázis, amiben több száz videóletöltő repo (yt-dlp, FFmpeg stb.) tudása van indexelve.

## 2. Hogyan csatlakozz?
Mivel egy külön GitHub repóban (sandboxban) vagy, fizikailag izolálva vagy a VPS-től. A kapcsolat felvételéhez a következőket kell tenned:

1. **Használd az SSH-t:** Ha van parancssori hozzáférésed, az `sshpass` segítségével (vagy privát kulccsal) tudsz csatlakozni:
   `sshpass -e ssh misi@5.189.163.88` (Jelszót a usertől kérj hozzá, ha nincs beállítva a környezetedben).
2. **Keresd a RAG-ot:** A munkádhoz ne a neten keress vakon. Használd a RAG adatbázist a VPS-en.

## 3. A "Zero Trust" és a Szabályok
*   A VPS-en futó eszközöket (Tool calls) szigorú Python FastMCP validáció védi. Ne próbálj illegális bash parancsokat (`> /dev/null`, pipe, stb.) használni a rendszer megkerülésére, mert blokkolva leszel.
*   A te doméneden belül (`video_downloader_RAG`) szabad kezet kapsz az adatok olvasására, de a központi `Jules_ICA_Builder` mappába nem írhatsz.

## 4. Mit kell tenned az első bejelentkezéskor?
1. Lépj be a szerverre.
2. Vizsgáld meg a `/home/misi/video_downloader_RAG/` könyvtárat.
3. Kezdj el a videóletöltő projekten (böngésző kiterjesztések, content.js stb.) dolgozni az ott található RAG tudás segítségével.

*– Jules, az ICA Builder*
