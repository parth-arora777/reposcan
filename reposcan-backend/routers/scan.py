from fastapi import APIRouter
from models.schemas import ScanReport, ScanRequest
from services.pipeline import run_scan

router = APIRouter(prefix="/api", tags=["scan"])


@router.post("/scan", response_model=ScanReport)
async def scan_repo(body: ScanRequest) -> ScanReport:
    return await run_scan(
        repo_url=body.repo_url,
        anthropic_api_key=body.anthropic_api_key,
        github_token=body.github_token,
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "RepoScan API"}