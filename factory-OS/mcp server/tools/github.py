"""GitHub API tools. Requires GITHUB_TOKEN with only the scopes needed."""
import os
import requests

API = "https://api.github.com"
TIMEOUT = 15


def _headers():
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured in the server environment")
    return {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"}


def github_list_my_repositories(per_page: int = 20):
    per_page = max(1, min(int(per_page), 100))
    response = requests.get(f"{API}/user/repos", headers=_headers(), params={"per_page": per_page, "sort": "updated"}, timeout=TIMEOUT)
    response.raise_for_status()
    return [{"name": r["name"], "full_name": r["full_name"], "private": r["private"], "html_url": r["html_url"], "default_branch": r.get("default_branch")} for r in response.json()]


def github_get_user_repositories(username: str, per_page: int = 20):
    if not username.strip() or "/" in username:
        raise ValueError("Provide a valid GitHub username")
    per_page = max(1, min(int(per_page), 100))
    response = requests.get(f"{API}/users/{username}/repos", params={"per_page": per_page, "sort": "updated"}, timeout=TIMEOUT)
    response.raise_for_status()
    return [{"name": r["name"], "full_name": r["full_name"], "private": r["private"], "html_url": r["html_url"], "description": r.get("description")} for r in response.json()]


def github_create_repository(name: str, description: str = "", private: bool = True):
    if not name.strip() or len(name) > 100:
        raise ValueError("Repository name must be 1-100 characters")
    response = requests.post(f"{API}/user/repos", headers=_headers(), json={"name": name, "description": description, "private": bool(private), "auto_init": True}, timeout=TIMEOUT)
    response.raise_for_status()
    repo = response.json()
    return {"full_name": repo["full_name"], "private": repo["private"], "html_url": repo["html_url"], "clone_url": repo["clone_url"]}


def github_put_file(owner: str, repo: str, path: str, content: str, commit_message: str = "Update file via Factory OS"):
    """Create or update a file. This writes to GitHub; use only with authorized credentials."""
    import base64
    if not all([owner.strip(), repo.strip(), path.strip()]):
        raise ValueError("owner, repo, and path are required")
    url = f"{API}/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
    headers = _headers()
    existing = requests.get(url, headers=headers, timeout=TIMEOUT)
    payload = {"message": commit_message, "content": base64.b64encode(content.encode("utf-8")).decode("ascii")}
    if existing.status_code == 200:
        payload["sha"] = existing.json()["sha"]
    elif existing.status_code != 404:
        existing.raise_for_status()
    response = requests.put(url, headers=headers, json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    result = response.json()
    return {"path": result["content"]["path"], "html_url": result["content"]["html_url"], "commit_sha": result["commit"]["sha"]}
