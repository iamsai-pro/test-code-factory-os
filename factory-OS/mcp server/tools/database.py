"""Read-only SQLite query tool. Database files are restricted to workspace/ databases."""
import sqlite3
from .filesystem import resolve_workspace_path


def sqlite_query(database_file: str, sql: str, params_json: str = "[]"):
    if not sql.strip():
        raise ValueError("SQL is required")
    if not sql.lstrip().upper().startswith(("SELECT", "WITH", "PRAGMA TABLE_INFO", "PRAGMA DATABASE_LIST")):
        raise ValueError("Read-only tool: only SELECT, WITH, and limited PRAGMA queries are allowed")
    params = __import__("json").loads(params_json)
    if not isinstance(params, list):
        raise ValueError("params_json must be a JSON array")
    path = resolve_workspace_path(database_file)
    if not path.is_file() or path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("database_file must be an existing SQLite database inside workspace/")
    uri = path.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, params)
        rows = [dict(row) for row in cur.fetchmany(500)]
        return {"columns": [c[0] for c in cur.description or []], "rows": rows, "returned_rows": len(rows), "truncated": len(rows) == 500}
    finally:
        conn.close()
