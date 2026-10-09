"""Workspace-only filesystem tools. Paths cannot escape the configured workspace."""
import hashlib
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1] / "workspace"
WORKSPACE.mkdir(parents=True, exist_ok=True)


def resolve_workspace_path(relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("A relative path is required")
    candidate = (WORKSPACE / relative_path).resolve()
    root = WORKSPACE.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path is outside the Factory OS workspace")
    return candidate


def list_files(relative_path: str = "."):
    target = resolve_workspace_path(relative_path)
    if not target.exists():
        raise FileNotFoundError(relative_path)
    if not target.is_dir():
        raise ValueError("Path is not a directory")
    items = []
    for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        items.append({"name": child.name, "type": "directory" if child.is_dir() else "file",
                      "size_bytes": child.stat().st_size if child.is_file() else None})
    return items


def read_text_file(relative_path: str, max_chars: int = 30000):
    target = resolve_workspace_path(relative_path)
    if not target.is_file():
        raise FileNotFoundError(relative_path)
    if target.stat().st_size > max_chars * 4:
        raise ValueError("File is too large for this tool; use a smaller file")
    return target.read_text(encoding="utf-8")[:max_chars]


def write_text_file(relative_path: str, content: str, overwrite: bool = False):
    target = resolve_workspace_path(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise FileExistsError("File already exists; set overwrite=true to replace it")
    if len(content) > 1_000_000:
        raise ValueError("Content exceeds 1 MB limit")
    target.write_text(content, encoding="utf-8")
    return {"success": True, "path": str(target.relative_to(WORKSPACE)), "bytes_written": target.stat().st_size}


def search_text_files(query: str, relative_path: str = ".", max_results: int = 20):
    if not query:
        raise ValueError("query cannot be empty")
    max_results = max(1, min(int(max_results), 100))
    root = resolve_workspace_path(relative_path)
    candidates = [root] if root.is_file() else root.rglob("*")
    results = []
    for path in candidates:
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".zip", ".exe", ".db"}:
            continue
        try:
            for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if query.casefold() in line.casefold():
                    results.append({"path": str(path.relative_to(WORKSPACE)), "line": line_no, "text": line[:500]})
                    if len(results) >= max_results:
                        return results
        except OSError:
            continue
    return results


def sha256_file(relative_path: str):
    target = resolve_workspace_path(relative_path)
    if not target.is_file():
        raise FileNotFoundError(relative_path)
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(target.relative_to(WORKSPACE)), "sha256": digest.hexdigest(), "size_bytes": target.stat().st_size}
