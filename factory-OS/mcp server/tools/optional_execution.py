"""Opt-in execution tools. These are NOT a security sandbox; keep disabled by default."""
import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1] / "workspace"


def _enabled():
    if os.getenv("FACTORY_OS_ENABLE_UNSAFE_TOOLS", "false").lower() not in {"1", "true", "yes"}:
        raise PermissionError("Execution tools are disabled. Set FACTORY_OS_ENABLE_UNSAFE_TOOLS=true only for trusted local development.")


def run_python(code: str, timeout_seconds: int = 5):
    _enabled()
    if not code.strip() or len(code) > 20000:
        raise ValueError("Code must be non-empty and at most 20,000 characters")
    ast.parse(code)
    timeout_seconds = max(1, min(int(timeout_seconds), 10))
    with tempfile.TemporaryDirectory(prefix="factory_os_exec_", dir=str(WORKSPACE)) as tmp:
        script = Path(tmp) / "main.py"
        script.write_text(code, encoding="utf-8")
        try:
            result = subprocess.run([sys.executable, "-I", str(script)], cwd=tmp, capture_output=True, text=True, timeout=timeout_seconds, shell=False)
            return {"success": result.returncode == 0, "returncode": result.returncode, "stdout": result.stdout[-8000:], "stderr": result.stderr[-8000:], "warning": "This is not a secure sandbox. Do not run untrusted code."}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timed out after {timeout_seconds} seconds"}


def run_terminal(command: str, timeout_seconds: int = 5):
    _enabled()
    if not command.strip():
        raise ValueError("command is required")
    # Deliberately tiny allowlist; no shell parsing and no shell=True.
    import shlex
    parts = shlex.split(command, posix=(os.name != "nt"))
    if not parts:
        raise ValueError("command is required")
    executable = Path(parts[0]).name.lower()
    allowed = {"python", "python3", "git", "node", "npm", "echo"}
    if executable not in allowed:
        raise PermissionError(f"Command '{executable}' is not allowlisted")
    timeout_seconds = max(1, min(int(timeout_seconds), 10))
    try:
        result = subprocess.run(parts, cwd=WORKSPACE, capture_output=True, text=True, timeout=timeout_seconds, shell=False)
        return {"success": result.returncode == 0, "returncode": result.returncode, "stdout": result.stdout[-8000:], "stderr": result.stderr[-8000:], "warning": "This is not a secure sandbox. Only enable for trusted local development."}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timed out after {timeout_seconds} seconds"}
