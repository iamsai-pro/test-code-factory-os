"""PDF text extraction restricted to workspace/ files."""
from .filesystem import resolve_workspace_path


def read_pdf(relative_path: str, max_pages: int = 50, max_chars: int = 40000):
    path = resolve_workspace_path(relative_path)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError("Provide a PDF file inside the workspace/")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc
    reader = PdfReader(str(path))
    chunks = []
    for page_num, page in enumerate(reader.pages[:max(1, min(int(max_pages), 100))], start=1):
        text = page.extract_text() or ""
        if text:
            chunks.append(f"--- Page {page_num} ---\n{text}")
        if sum(len(c) for c in chunks) >= max_chars:
            break
    output = "\n\n".join(chunks)
    return {"path": relative_path, "page_count": len(reader.pages), "extracted_characters": min(len(output), max_chars), "text": output[:max_chars]}
