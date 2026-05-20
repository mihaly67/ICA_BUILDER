#!/usr/bin/env python3
"""
MQL5 Theory TOC (Tartalomjegyzék) Olvasó Szikra (Spark)
Ez a script lehetővé teszi az EA Jules számára, hogy emberi módra, a tartalomjegyzéket
elemezve ugorjon a szakkönyvek pontos oldalaira, elkerülve a vaktában történő vektoros keresést.
"""
import os
import sqlite3
import re
import json
import argparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mql5_native_knowledge.db")

def fetch_page_content(book_prefix, page_num):
    """Lekéri egy konkrét oldal tartalmát az adatbázisból."""
    if not os.path.exists(DB_PATH):
        return f"Hiba: Az adatbázis nem található itt: {DB_PATH}"

    filepath_key = f"{book_prefix}_Page_{page_num}"
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM rag_data WHERE filepath = ?", (filepath_key,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        return None
    except Exception as e:
        return f"Hiba a DB olvasásakor: {e}"

def extract_toc_from_book(book_prefix, toc_pages_range=(2, 25)):
    """
    Felolvassa az első X oldalt a könyvből (ahol a Contents található),
    és regex segítségével kinyeri a fejezetcímeket és az oldalszámokat.
    """
    toc_mapping = []

    for page in range(toc_pages_range[0], toc_pages_range[1] + 1):
        content = fetch_page_content(book_prefix, page)
        if not content:
            continue

        lines = content.split('\n')
        current_title = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Eltávolítjuk a markdown headingeket ha benne maradtak
            if line.startswith("#"):
                continue

            # Ha csak pontok és szám a sor (pl "....... 12")
            match_dots_number = re.match(r'^\.{3,}\s*(\d+)$', line)
            if match_dots_number and current_title:
                page_num = match_dots_number.group(1)
                if len(current_title) > 2 and current_title.lower() != "contents" and not current_title.isdigit():
                    toc_mapping.append({
                        "chapter": current_title.strip(),
                        "page": int(page_num)
                    })
                current_title = "" # Reset
                continue

            # Ha egy sorban van az egész (pl "1.1 Title ...... 12")
            match_inline = re.match(r'^(.+?)\.{3,}\s*(\d+)$', line)
            if match_inline:
                title = match_inline.group(1).strip()
                page_num = match_inline.group(2)
                if len(title) > 2 and title.lower() != "contents" and not title.isdigit():
                    toc_mapping.append({
                        "chapter": title,
                        "page": int(page_num)
                    })
                current_title = "" # Reset
                continue

            # Ha nem illeszkedik a pontozásra, de értelmes címnek tűnik
            if not re.match(r'^\d+$', line) and len(line) > 3:
                 current_title = line

    return toc_mapping

def get_chapter_content(book_prefix, chapter_keyword, max_pages=3):
    """
    Megkeresi a kulcsszó alapján a fejezetet a TOC-ban, és felolvassa az onnan kezdődő oldalakat.
    """
    toc = extract_toc_from_book(book_prefix)

    # Keressünk a tartalomjegyzékben
    found_chapters = []
    for entry in toc:
        if chapter_keyword.lower() in entry['chapter'].lower():
            found_chapters.append(entry)

    if not found_chapters:
        return json.dumps({"error": f"Nem találtam '{chapter_keyword}' a tartalomjegyzékben."}, ensure_ascii=False)

    # Vesszük a legelső (legpontosabb) találatot
    best_match = found_chapters[0]
    start_page = best_match['page']

    result = {
        "chapter_found": best_match['chapter'],
        "start_page": start_page,
        "content": ""
    }

    full_text = f"--- FEJEZET: {best_match['chapter']} (Oldal: {start_page}) ---\n\n"
    for p in range(start_page, start_page + max_pages):
        page_text = fetch_page_content(book_prefix, p)
        if page_text:
            full_text += f"\n\n[--- PAGE {p} ---]\n" + page_text

    result["content"] = full_text
    return json.dumps(result, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQL5 Könyv TOC és Oldal Olvasó")
    parser.add_argument("--book", type=str, required=True, help="A könyv előtagja (pl. neuronetworksbook.md vagy mql5book.md)")
    parser.add_argument("--action", choices=["toc", "read_chapter", "read_page"], required=True, help="Mit szeretnél csinálni?")
    parser.add_argument("--query", type=str, help="Fejezet címe vagy kulcsszava (read_chapter esetén)")
    parser.add_argument("--page", type=int, help="Pontos oldalszám (read_page esetén)")
    parser.add_argument("--pages", type=int, default=3, help="Hány oldalt olvasson fel a fejezettől kezdve")

    args = parser.parse_args()

    if args.action == "toc":
        toc = extract_toc_from_book(args.book)
        print(json.dumps(toc, ensure_ascii=False, indent=2))

    elif args.action == "read_chapter":
        if not args.query:
            print(json.dumps({"error": "A --query paraméter kötelező a read_chapter-hez!"}))
        else:
            print(get_chapter_content(args.book, args.query, args.pages))

    elif args.action == "read_page":
        if not args.page:
            print(json.dumps({"error": "A --page paraméter kötelező a read_page-hez!"}))
        else:
            content = fetch_page_content(args.book, args.page)
            if content:
                print(content)
            else:
                print(f"A(z) {args.page}. oldal nem található a(z) {args.book} könyvben.")
