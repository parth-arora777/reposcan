import base64
import re
from typing import Optional

import httpx
from fastapi import HTTPException

from models.schemas import RepoMeta, ParsedRepo

GITHUB_API = "https://api.github.com"

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".rb", ".php", ".cs", ".cpp", ".c", ".swift", ".kt", ".scala",
}
MAX_CODE_CHARS = 6000
MAX_README_CHARS = 4000


def _make_headers(token: Optional[str]) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def parse_github_url(url: str) -> tuple[str, str]:
    match = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", url)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL. Expected: https://github.com/owner/repo"
        )
    owner = match.group(1)
    repo = match.group(2).removesuffix(".git")
    return owner, repo


async def fetch_repo(url: str, token: Optional[str] = None) -> ParsedRepo:
    owner, repo = parse_github_url(url)
    headers = _make_headers(token)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}",
            headers=headers
        )
        if r.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Repository {owner}/{repo} not found or is private."
            )
        if r.status_code == 403:
            raise HTTPException(
                status_code=429,
                detail="GitHub rate limit hit. Add a GitHub token in .env."
            )
        r.raise_for_status()
        raw = r.json()

        meta = RepoMeta(
            full_name=raw["full_name"],
            description=raw.get("description"),
            language=raw.get("language"),
            stars=raw.get("stargazers_count", 0),
            forks=raw.get("forks_count", 0),
            html_url=raw["html_url"],
            topics=raw.get("topics", []),
        )

        readme_text = await _fetch_readme(client, owner, repo, headers)
        file_names, code_files = await _fetch_file_tree(client, owner, repo, headers)
        code_sample = await _fetch_code_sample(client, owner, repo, code_files, headers)

    return ParsedRepo(
        meta=meta,
        readme=readme_text[:MAX_README_CHARS],
        file_names=file_names,
        code_sample=code_sample,
    )


async def _fetch_readme(client, owner, repo, headers) -> str:
    try:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/readme",
            headers=headers
        )
        if r.status_code != 200:
            return ""
        data = r.json()
        content = base64.b64decode(
            data["content"].replace("\n", "")
        ).decode("utf-8", errors="ignore")
        return content
    except Exception:
        return ""


async def _fetch_file_tree(client, owner, repo, headers) -> tuple[list[str], list[dict]]:
    try:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1",
            headers=headers
        )
        if r.status_code != 200:
            r2 = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contents",
                headers=headers
            )
            items = r2.json() if r2.status_code == 200 else []
            file_names = [i["name"] for i in items if i.get("type") == "file"]
            code_files = [
                i for i in items
                if i.get("type") == "file" and _is_code(i["name"])
            ][:5]
            return file_names, code_files

        tree = r.json().get("tree", [])
        blobs = [t for t in tree if t["type"] == "blob"]
        file_names = [b["path"] for b in blobs]

        code_files = []
        for b in blobs:
            if len(code_files) >= 5:
                break
            path = b["path"]
            size = b.get("size", 0)
            depth = path.count("/")
            if _is_code(path) and size < 50000 and depth <= 2:
                code_files.append({
                    "path": path,
                    "url": b.get("url", "")
                })

        return file_names, code_files
    except Exception:
        return [], []


def _is_code(path: str) -> bool:
    return any(path.endswith(ext) for ext in CODE_EXTENSIONS)


async def _fetch_code_sample(client, owner, repo, code_files, headers) -> str:
    combined = ""
    for f in code_files:
        if len(combined) >= MAX_CODE_CHARS:
            break
        try:
            path = f.get("path", "")
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                headers=headers
            )
            if r.status_code != 200:
                continue
            data = r.json()
            content = base64.b64decode(
                data["content"].replace("\n", "")
            ).decode("utf-8", errors="ignore")
            remaining = MAX_CODE_CHARS - len(combined)
            combined += f"\n\n// === {path} ===\n" + content[:remaining]
        except Exception:
            continue
    return combined


async def search_similar(
    keywords: list[str],
    language: Optional[str],
    exclude: str,
    token: Optional[str] = None,
) -> list[dict]:
    headers = _make_headers(token)
    q = " ".join(keywords[:4])
    lang_filter = f" language:{language}" if language else ""
    query = f"{q} in:description,readme,name{lang_filter}"

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            r = await client.get(
                f"{GITHUB_API}/search/repositories",
                params={"q": query, "sort": "stars", "per_page": 8},
                headers=headers,
            )
            if r.status_code != 200:
                return []
            items = r.json().get("items", [])
            return [i for i in items if i["full_name"] != exclude][:5]
        except Exception:
            return []