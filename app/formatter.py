import discord


CATEGORY_LABELS = {
    "ai_agent": "AI Agent",
    "ai_code": "AI Coding",
    "mcp": "MCP",
    "ai_tools": "AI Tools",
    "rag": "RAG",
    "llm": "LLM",
    "other": "AI / Other",
}


def build_embed(repo: dict, category: str, score: int, reason: str, llm: dict | None = None):
    label = CATEGORY_LABELS.get(category, category)
    title = f"NEW AI REPOSITORY — {repo['full_name']}"

    description = repo.get("description") or "No description provided."

    if llm:
        summary = llm.get("summary")
        why = llm.get("why_it_matters")
        if summary:
            description = summary
        if why:
            reason = why

    embed = discord.Embed(
        title=title[:256],
        url=repo["html_url"],
        description=description[:4096],
        color=discord.Color.blurple(),
    )

    embed.add_field(name="Category", value=label, inline=True)
    embed.add_field(name="Score", value=f"{score}/100", inline=True)
    embed.add_field(
        name="Language",
        value=repo.get("language") or "Unknown",
        inline=True,
    )
    embed.add_field(
        name="Stars",
        value=str(repo.get("stargazers_count", 0)),
        inline=True,
    )
    embed.add_field(
        name="Forks",
        value=str(repo.get("forks_count", 0)),
        inline=True,
    )
    embed.add_field(
        name="Created",
        value=(repo.get("created_at") or "Unknown")[:19].replace("T", " "),
        inline=True,
    )
    embed.add_field(name="Why / Signals", value=reason[:1024], inline=False)

    if llm and llm.get("features"):
        features = "\n".join(f"• {x}" for x in llm["features"][:5])
        embed.add_field(name="Features", value=features[:1024], inline=False)

    topics = repo.get("topics") or []
    if topics:
        embed.add_field(
            name="Topics",
            value=" ".join(f"`{x}`" for x in topics[:12])[:1024],
            inline=False,
        )

    owner = repo.get("owner", {})
    if owner.get("avatar_url"):
        embed.set_thumbnail(url=owner["avatar_url"])

    embed.set_footer(text="AI Repo Radar")
    return embed
