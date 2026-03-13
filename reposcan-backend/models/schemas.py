from pydantic import BaseModel, HttpUrl
from typing import Optional


# ── Request ──────────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    repo_url: str
    anthropic_api_key: Optional[str] = None
    github_token: Optional[str] = None


# ── GitHub layer ──────────────────────────────────────────────────────────────

class RepoMeta(BaseModel):
    full_name: str
    description: Optional[str]
    language: Optional[str]
    stars: int
    forks: int
    html_url: str
    topics: list[str] = []


class ParsedRepo(BaseModel):
    meta: RepoMeta
    readme: str
    file_names: list[str]
    code_sample: str


# ── Analysis layer ────────────────────────────────────────────────────────────

class RepoDescription(BaseModel):
    summary: str
    keywords: list[str]
    category: str
    unique_approach: str


class SimilarRepo(BaseModel):
    full_name: str
    description: Optional[str]
    stars: int
    language: Optional[str]
    html_url: str
    topics: list[str] = []


class Differentiator(BaseModel):
    type: str
    text: str


class FlaggedFile(BaseModel):
    file: str
    reason: str
    similarity: int


class ComparisonResult(BaseModel):
    originality_score: int
    code_similarity: int
    idea_novelty: int
    originality_label: str
    verdict: str
    differentiators: list[Differentiator]
    flagged_files: list[FlaggedFile]
    top_match: Optional[str]


# ── Final report ──────────────────────────────────────────────────────────────

class ScanReport(BaseModel):
    repo: RepoMeta
    description: RepoDescription
    similar_repos: list[SimilarRepo]
    comparison: ComparisonResult