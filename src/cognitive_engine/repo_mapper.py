import os
import ast

def generate_repo_map(root_dir, output_file="RepoMap.md"):
    """
    A 'Bloop' és az 'Aider' elveit követve generál egy kognitív térképet a repóról.
    Nem a teljes kódot olvassa be, csak a mappastruktúrát, valamint a Python fájlok
    osztályait (class) és függvényeit (def). Ezt az LLM azonnal megérti.
    """
    ignore_dirs = {'.git', '__pycache__', 'venv', 'node_modules', 'dist', 'build'}

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# KOGNITÍV REPO TÉRKÉP (TARTALOMJEGYZÉK)\n\n")

        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

            level = dirpath.replace(root_dir, '').count(os.sep)
            indent = ' ' * 4 * level
            f.write(f"{indent}📁 {os.path.basename(dirpath)}/\n")

            sub_indent = ' ' * 4 * (level + 1)
            for filename in filenames:
                f.write(f"{sub_indent}📄 {filename}\n")

                # Ha Python fájl, kinyerjük az AST-t (Abstract Syntax Tree)
                if filename.endswith('.py'):
                    filepath = os.path.join(dirpath, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as pf:
                            tree = ast.parse(pf.read(), filename=filepath)
                            for node in tree.body:
                                if isinstance(node, ast.ClassDef):
                                    f.write(f"{sub_indent}    🧩 class {node.name}\n")
                                elif isinstance(node, ast.FunctionDef):
                                    f.write(f"{sub_indent}    ⚙️ def {node.name}()\n")
                    except Exception as e:
                        f.write(f"{sub_indent}    ⚠️ Parse hiba: {e}\n")

if __name__ == "__main__":
    # Generálunk egy térképet erről a repóról
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    generate_repo_map(repo_root, os.path.join(repo_root, "KOGNITIV_REPO_TERKEP.md"))
    print("✅ Kognitív Repo Térkép sikeresen legenerálva!")
