import asyncio
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import aiohttp


log = logging.getLogger(__name__)


class GitHubClient:
    BASE = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "AI-Repo-Radar-Discord",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def _get(self, path: str, params: dict | None = None):
        assert self.session is not None

        for attempt in range(3):
            async with self.session.get(self.BASE + path, params=params) as r:
                if r.status == 200:
                    return await r.json()

                if r.status in (403, 429):
                    retry_after = r.headers.get("Retry-After")
                    wait = int(retry_after) if retry_after and retry_after.isdigit() else 60
                    log.warning("GitHub rate limited. Waiting %ss", wait)
                    await asyncio.sleep(wait)
                    continue

                body = await r.text()
                raise RuntimeError(f"GitHub API {r.status}: {body[:500]}")

        raise RuntimeError("GitHub API gagal setelah retry.")

    async def search_repositories(
        self, query: str, lookback_hours: int, per_page: int = 20
    ) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        q = f"{query} created:>={since.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        data = await self._get(
            "/search/repositories",
            params={
                "q": q,
                "sort": "updated",
                "order": "desc",
                "per_page": min(per_page, 100),
            },
        )
        return data.get("items", [])

    async def readme(self, full_name: str) -> str:
        owner, repo = full_name.split("/", 1)
        data = await self._get(f"/repos/{quote(owner)}/{quote(repo)}/readme")
        # README endpoint returns base64 content; decoding is deliberately omitted
        # because the search pipeline only needs a compact metadata analysis.
        return data.get("name", "")
