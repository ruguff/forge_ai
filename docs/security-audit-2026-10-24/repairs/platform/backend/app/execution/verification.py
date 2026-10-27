"""Content fingerprints prevent stale verification from authorizing changed code."""
import hashlib
from pathlib import Path


def source_digest(root):
    root = Path(root).resolve()
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in (".git", ".projectforge", "node_modules", ".venv", "venv", "dist", "__pycache__", ".pytest_cache") for part in relative.parts):
            continue
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Source fingerprints do not permit linked paths.")
        if path.is_file():
            digest.update(relative.as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()
