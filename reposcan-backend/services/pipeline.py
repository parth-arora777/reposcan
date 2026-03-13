from config import get_settings
from models.schemas import ScanReport, SimilarRepo
from services import claude as claude_svc
from services import github as github_svc


async def run_scan(
    repo_url: str,
    anthropic_api_key: str | None,
    github_token: str | None,
) -> ScanReport:
    settings = get_settings()

    gh_token = github_token or settings.github_token or None
    ant_key = anthropic_api_key or settings.groq_api_key
    if not ant_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No Anthropic API key provided.")

    # Step 1: Fetch repo
    parsed = await github_svc.fetch_repo(repo_url, token=gh_token)

    # Step 2: Claude reads README
    description = await claude_svc.describe_repo(parsed, api_key=ant_key)

    # Step 3: Search similar repos
    raw_similar = await github_svc.search_similar(
        keywords=description.keywords,
        language=parsed.meta.language,
        exclude=parsed.meta.full_name,
        token=gh_token,
    )

    similar_repos = [
        SimilarRepo(
            full_name=r["full_name"],
            description=r.get("description"),
            stars=r.get("stargazers_count", 0),
            language=r.get("language"),
            html_url=r["html_url"],
            topics=r.get("topics", []),
        )
        for r in raw_similar
    ]

    # Step 4: Claude compares + scores
    comparison = await claude_svc.compare_repos(
        parsed=parsed,
        description=description,
        similar_repos=raw_similar,
        api_key=ant_key,
    )

    return ScanReport(
        repo=parsed.meta,
        description=description,
        similar_repos=similar_repos,
        comparison=comparison,
    )