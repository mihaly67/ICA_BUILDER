import sqlite3

db_path = "/home/misi/MX_LINUX_RAG/mx_linux_knowledge.db"
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Próbáljuk újra egy tisztább lekérdezéssel, ami tényleg a dpkg force-ra fókuszál
    cursor.execute("SELECT content FROM rag_data WHERE content LIKE '%dpkg --remove --force%' OR content LIKE '%dpkg --purge --force%' OR content LIKE '%dpkg -r --force%' LIMIT 2;")
    results = cursor.fetchall()
    for row in results:
        print(row[0][:500])
        print("...\n")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
