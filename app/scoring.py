import re


class Scorer:
    def __init__(self, categories: dict, negative_keywords: list[str]):
        self.categories = categories
        self.negative_keywords = [x.lower() for x in negative_keywords]

    def score(self, repo: dict) -> tuple[int, str, list[str]]:
        text = " ".join(
            str(repo.get(k) or "")
            for k in ("name", "description", "topics", "language")
        ).lower()

        matched = []
        category_scores = []

        for category, spec in self.categories.items():
            hits = []
            for keyword in spec.get("keywords", []):
                if keyword.lower() in text:
                    hits.append(keyword)
            if hits:
                matched.append(f"{category}: {', '.join(hits[:3])}")
                category_scores.append(int(spec.get("weight", 0)))

        negative_hits = [
            k for k in self.negative_keywords
            if re.search(r"\b" + re.escape(k) + r"\b", text)
        ]

        score = min(100, sum(sorted(category_scores, reverse=True)[:3]))

        if repo.get("has_issues"):
            score += 2
        if repo.get("has_wiki"):
            score += 1
        if repo.get("license"):
            score += 3
        if repo.get("stargazers_count", 0) >= 10:
            score += 5
        if repo.get("stargazers_count", 0) >= 100:
            score += 8
        if repo.get("forks_count", 0) >= 10:
            score += 2

        if repo.get("fork"):
            score -= 30
            matched.append("fork")

        if negative_hits:
            score -= min(25, len(negative_hits) * 5)
            matched.append("negative: " + ", ".join(negative_hits[:4]))

        score = max(0, min(100, score))

        category = self._pick_category(category_scores, matched)
        reason = "; ".join(matched[:6]) or "Tidak ada sinyal kategori kuat."
        return score, category, reason

    def _pick_category(self, scores, matched):
        if not matched:
            return "other"
        names = [m.split(":", 1)[0] for m in matched if ":" in m]
        if not names:
            return "other"
        # The first matched category is sufficient because config ordering
        # is intentionally meaningful.
        return names[0]
