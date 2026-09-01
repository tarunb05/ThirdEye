from pathlib import Path

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt",
    ".kts", ".scala", ".sh", ".bat", ".ps1",
    ".html", ".css", ".scss", ".sass", ".xml", ".json",
    ".yaml", ".yml", ".sql", ".md"
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "dist", "build",
    ".venv", "venv", "target", ".idea", ".vscode", ".next",
    ".cache", "coverage", "out", "bin", "obj"
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "directory_recursor_output.txt"
}

MAX_FILE_SIZE = 1_000_000  # 1 MB


def is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS and path.name not in SKIP_FILES


def main():
    script_dir = Path(__file__).parent.resolve()
    output_file = script_dir / "directory_recursor_output.txt"

    collected = []

    for file_path in script_dir.rglob("*"):
        if not file_path.is_file():
            continue

        if any(part in SKIP_DIRS for part in file_path.parts):
            continue

        if not is_code_file(file_path):
            continue

        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                collected.append((file_path, "[Skipped: file too large]\n"))
                continue

            content = file_path.read_text(encoding="utf-8", errors="replace")
            collected.append((file_path, content))
        except Exception as e:
            collected.append((file_path, f"[Error reading file: {e}]\n"))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("DIRECTORY RECURSOR OUTPUT\n")
        f.write(f"Scanned directory: {script_dir}\n")
        f.write(f"Total files collected: {len(collected)}\n")
        f.write("=" * 100 + "\n\n")

        for file_path, content in collected:
            relative_path = file_path.relative_to(script_dir)
            f.write("=" * 100 + "\n")
            f.write(f"FILE: {relative_path}\n")
            f.write("=" * 100 + "\n\n")
            f.write(content)
            f.write("\n\n")

    print(f"Done. Output written to: {output_file}")


if __name__ == "__main__":
    main()