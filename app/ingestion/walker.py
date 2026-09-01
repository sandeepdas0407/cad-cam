import hashlib
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def discover_files(folders: list[Path]) -> list[Path]:
    files = []
    for folder in folders:
        if not folder.exists():
            continue
        for p in folder.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if p.name.startswith("~$"):  # Word lock files
                continue
            files.append(p)
    return files


def file_fingerprint(path: Path) -> tuple[int, float]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
