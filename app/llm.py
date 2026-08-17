import logging
import json
import aiohttp


log = logging.getLogger(__name__)


class OllamaAnalyzer:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def analyze(self, repo: dict, category: str, score: int) -> dict:
        prompt = f'''
Analyze this GitHub repository for an AI developer community.

Repository: {repo.get("full_name")}
Description: {repo.get("description")}
Language: {repo.get("language")}
Stars: {repo.get("stargazers_count", 0)}
Forks: {repo.get("forks_count", 0)}
Category: {category}
Initial score: {score}

Return ONLY valid JSON:
{{
  "summary": "1-2 sentence summary",
  "why_it_matters": "short explanation",
  "features": ["feature 1", "feature 2", "feature 3"],
  "risk": "low|medium|high"
}}
'''
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{self.base_url}/api/generate", json=payload) as r:
                if r.status != 200:
                    raise RuntimeError(f"Ollama HTTP {r.status}")
                data = await r.json()
                raw = data.get("response", "{}")
                return json.loads(raw)
