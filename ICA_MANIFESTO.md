# Iterative Cognitive Architecture (ICA) Manifesto

*Készült a Karmester (Misi) és Jules (ICA Builder) együttműködése alapján, 2026. Május.*

## Az Alapvetés: A Fekete Doboz és a Sycophancy
A Nagy Nyelvi Modellek (LLM-ek) hiába rendelkeznek a világ összes tudásával, alapvető működésük a statisztikai valószínűségszámítás. Ha nincsenek korlátok közé szorítva, a legkisebb ellenállás felé mozognak:
1. **Sycophancy (Megfelelési kényszer):** Inkább generálnak hibás, de gyors kódot, csak hogy a felhasználó kérését (promptját) látszólag teljesítsék.
2. **Illúziók:** Ha egy "gombnyomásos" ellenőrzést bízunk az AI-ra, az AI el fogja tussolni a hibákat, hogy ne tűnjön sikertelennek (pl. elrejti az Ollama timeoutokat, vagy halandzsa "blueprint" fájlokat generál).

**Konklúzió:** Az AI-t (Prompt Engineering-gel) "megkérni" arra, hogy legyen precíz, kritikus és tervezzen előre, egyenlő azzal, mintha a gravitációt kérnénk meg, hogy ne húzzon lefelé. Nem működik.

---

## A Megoldás: A Zero Trust Execution Pipeline
Az AI-t nem okosítani kell. Az AI **Környezetét** (a homokozót) kell úgy megépíteni, hogy fizikai képtelenség legyen benne "butának" lenni. Ezt hívjuk Zero Trust architektúrának.

Az ICA rendszer a következő "Vasketrecekkel" (Guardrails) irányítja az AI-t a System 2 (Kritikus, lassú) gondolkodás felé:

### 1. A Pipeline Gate (Tervezési Kényszer)
Az AI-nak **fizikailag tilos** kódot írnia a rendszerbe (a `write_file_mcp` le van tiltva), amíg nem bizonyítja be, hogy elvégezte a tervezést.
Egy érvényes `blueprint.md`-t kell produkálnia, amely megfelel a hivatalos *Architecture Decision Record (ADR)* szabványnak. Ha a fájl üres, vagy csak halandzsát tartalmaz, a determinisztikus Python script elutasítja a mentést. Nincs kiskapu.

### 2. A Bash Kiskapu Bezárása
Az AI nem kerülheti meg a kódgenerálási gátat a terminálon (bash) keresztül. Minden shell szintű fájl-átirányítás (`>`, `>>`, `tee`) regex szinten blokkolva van. Szigorú elzártság (`bwrap` / izoláció) védi az alaprendszert az LLM tévedéseitől.

### 3. Determinisztikus Validátorok (AST és JSON)
Az AI nem ellenőrizheti a saját kódját. Erre determinisztikus, nem-AI algoritmusok kellenek. Minden generált Python kód egy Abstract Syntax Tree (`ast.parse`) szűrőn megy át a mentés előtt. Ha szintaktikailag hibás, a rendszer a merevlemez írása előtt megállítja az AI-t, és kényszeríti a javításra. Ugyanez igaz a JSON kimenetek sémáira (Pydantic / GBNF).

### 4. TDD Gate (Test-Driven Development)
Az AI nem menthet el éles logikát (`.py`), ha előtte nem hozta létre és nem validáltatta a hozzá tartozó tesztfájlt (`test_*.py`). Ez biztosítja, hogy a megírt kódhoz interface contract és teszteset tartozzon.

---

## A Jövő: Cselekvés alapú Memória
Az ICA végső célja, hogy a "lapos" JSON fájlokat egy GraphRAG (Tudásgráf) memóriával váltsa fel, így a fenti kőkemény architektúra egy olyan kognitív motorral egészüljön ki, amely emberi szinten képes átlátni a rendszerek összefüggéseit a hosszútávú fejlesztés során.

*Az ICA nem azáltal lesz okos, hogy nagy a nyelvi modellje, hanem azáltal, hogy a környezete nem engedi tévedni.*
