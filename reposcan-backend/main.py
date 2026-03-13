from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_settings
from routers.scan import router as scan_router
from services.pipeline import run_scan

settings = get_settings()

app = FastAPI(
    title="RepoScan API",
    description="Originality analysis for GitHub repositories",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan_router)


class AnalyseRequest(BaseModel):
    repo_url: str


@app.post("/analyse")
async def analyse(body: AnalyseRequest):
    import os
    api_key = settings.groq_api_key
    report = await run_scan(
        repo_url=body.repo_url,
        anthropic_api_key=api_key,
        github_token=settings.github_token,
    )
    return {
        "repo": report.repo.full_name,
        "files_scanned": len(report.description.keywords),
        "originality_score": report.comparison.originality_score,
        "code_similarity": report.comparison.code_similarity,
        "idea_novelty": report.comparison.idea_novelty,
        "verdict": report.comparison.verdict,
        "flagged_files": [f.file for f in report.comparison.flagged_files],
        "similar_projects": [r.full_name for r in report.similar_repos],
        "strengths": [d.text for d in report.comparison.differentiators if d.type == "positive"],
        "concerns": [d.text for d in report.comparison.differentiators if d.type == "negative"],
        "raw_similar": [
            {
                "name": r.full_name,
                "url": r.html_url,
                "description": r.description or "",
                "stars": r.stars,
            }
            for r in report.similar_repos
        ],
    }


@app.get("/")
async def root():
    return {
        "service": "RepoScan API",
        "docs": "/docs",
        "health": "/api/health",
        "scan": "POST /api/scan",
    }