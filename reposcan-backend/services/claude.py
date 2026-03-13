import json
import re
from typing import Optional

import httpx
from fastapi import HTTPException

from models.schemas import (
    ComparisonResult,
    Differentiator,
    FlaggedFile,
    ParsedRepo,
    RepoDescription,
)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def _safe_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    return json.loads(clean)


async def describe_repo(parsed: ParsedRepo, api_key: str) -> RepoDescription:
    prompt = f"""Analyze this GitHub project and produce a structured description.

REPO: {parsed.meta.full_name}
DESCRIPTION: {parsed.meta.description or "none"}
LANGUAGE: {parsed.meta.language or "unknown"}
STARS: {parsed.meta.stars}
TOPICS: {", ".join(parsed.meta.topics) or "none"}
FILES (sample): {", ".join(parsed.file_names[:25])}

README (first 3000 chars):
{parsed.readme[:3000]}

Respond ONLY with a JSON object, no markdown, no backticks, no extra text:
{{
  "summary": "<2 sentences: what this project does>",
  "keywords": ["<4-6 search keywords>"],
  "category": "<short category>",
  "unique_approach": "<1 sentence: what makes this distinctive>"
}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a code analysis expert. Always respond with pure JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            )
            if r.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Groq API key.")
            if r.status_code == 429:
                raise HTTPException(status_code=429, detail="Groq rate limit hit.")
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            result = _safe_json(text)
            return RepoDescription(
                summary=result.get("summary", parsed.meta.description or "A software project."),
                keywords=result.get("keywords", [parsed.meta.language or "software"]),
                category=result.get("category", "software tool"),
                unique_approach=result.get("unique_approach", "Standard implementation."),
            )
    except HTTPException:
        raise
    except Exception:
        return RepoDescription(
            summary=parsed.meta.description or "A software project.",
            keywords=[parsed.meta.language or "software"],
            category="software tool",
            unique_approach="Standard implementation.",
        )


async def compare_repos(
    parsed: ParsedRepo,
    description: RepoDescription,
    similar_repos: list[dict],
    api_key: str,
) -> ComparisonResult:
    repos_block = "\n".join(
        f"{i+1}. {r['full_name']} (stars:{r.get('stargazers_count',0)}) "
        f"{r.get('description') or 'No description'} [{r.get('language') or '?'}]"
        for i, r in enumerate(similar_repos)
    ) or "No similar repositories found."

    prompt = f"""You are a senior software architect performing an originality audit.

TARGET PROJECT: {parsed.meta.full_name}
CATEGORY: {description.category}
SUMMARY: {description.summary}
UNIQUE APPROACH: {description.unique_approach}
FILES: {", ".join(parsed.file_names[:20])}

CODE SAMPLE:
{parsed.code_sample[:4000] or "(no code retrieved)"}

SIMILAR PROJECTS:
{repos_block}

Respond ONLY with this JSON, no markdown, no backticks:
{{
  "originality_score": <0-100>,
  "code_similarity": <0-100>,
  "idea_novelty": <0-100>,
  "originality_label": "<label>",
  "verdict": "<2-3 sentence verdict>",
  "differentiators": [
    {{"type": "positive", "text": "<text>"}},
    {{"type": "negative", "text": "<text>"}}
  ],
  "flagged_files": [],
  "top_match": "<full_name or null>"
}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a senior software architect. Respond with pure JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 800
                }
            )
            if r.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Groq API key.")
            if r.status_code == 429:
                raise HTTPException(status_code=429, detail="Groq rate limit hit.")
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            result = _safe_json(text)
            return ComparisonResult(
                originality_score=int(result.get("originality_score", 50)),
                code_similarity=int(result.get("code_similarity", 50)),
                idea_novelty=int(result.get("idea_novelty", 50)),
                originality_label=result.get("originality_label", "Undetermined"),
                verdict=result.get("verdict", "Analysis inconclusive."),
                differentiators=[Differentiator(**d) for d in result.get("differentiators", [])],
                flagged_files=[FlaggedFile(**f) for f in result.get("flagged_files", [])],
                top_match=result.get("top_match"),
            )
    except HTTPException:
        raise
    except Exception as e:
        return ComparisonResult(
            originality_score=50,
            code_similarity=30,
            idea_novelty=60,
            originality_label="Analysis Incomplete",
            verdict=f"Analysis could not be completed: {str(e)[:100]}",
            differentiators=[],
            flagged_files=[],
            top_match=None,
        )