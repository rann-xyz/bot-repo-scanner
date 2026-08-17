import os
import asyncio
import hashlib
import sqlite3
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import aiohttp
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import feedparser

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))
DB_FILE = os.getenv("DB_FILE", "github_rss.db")

# GitHub Search supports Atom feeds for search pages.
# Change/add queries here if you want other AI categories.
SEARCH_QUERIES = [
    '"AI agent"',
    '"agentic AI"',
    '"coding agent"',
    '"AI coding"',
    '"MCP server"',
    '"Model Context Protocol"',
    '"AI tools"',
    '"LLM tools"',
    '"RAG"',
    '"LLM framework"',
]

GITHUB_SEARCH_ATOM = "https://github.com/search.atom"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def db():
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            published TEXT,
            created_at TEXT NOT NULL
        )
    """)
    con.commit()
    return con


def entry_id(entry):
    raw = (
        entry.get("id")
        or entry.get("link")
        or entry.get("title", "")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def already_seen(item_id):
    con = db()
    row = con.execute(
        "SELECT 1 FROM seen WHERE id = ?",
        (item_id,)
    ).fetchone()
    con.close()
    return row is not None


def mark_seen(item_id, url, title, published):
    con = db()
    con.execute(
        """
        INSERT OR IGNORE INTO seen
        (id, url, title, published, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            item_id,
            url,
            title,
            published,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    con.commit()
    con.close()


def clean_title(title):
    return title.replace("GitHub", "").strip(" -:")


def parse_date(entry):
    value = entry.get("published") or entry.get("updated") or ""

    try:
        dt = parsedate_to_datetime(value)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return value or "Unknown"


async def get_feed(session, query):
    params = {
        "q": f"{query} type:repositories",
        "type": "repositories",
    }

    headers = {
        "User-Agent": "GitHub-RSS-Discord-Bot/1.0",
        "Accept": "application/atom+xml",
    }

    async with session.get(
        GITHUB_SEARCH_ATOM,
        params=params,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:

        if response.status != 200:
            text = await response.text()
            raise RuntimeError(
                f"GitHub RSS HTTP {response.status}: {text[:200]}"
            )

        return await response.text()


async def scan_github(send_notifications=True):
    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        channel = await bot.fetch_channel(CHANNEL_ID)

    new_items = 0

    async with aiohttp.ClientSession() as session:
        for query in SEARCH_QUERIES:
            try:
                xml = await get_feed(session, query)
                feed = feedparser.parse(xml)

                for entry in feed.entries:
                    item_id = entry_id(entry)

                    if already_seen(item_id):
                        continue

                    title = clean_title(entry.get("title", "New GitHub repository"))
                    url = entry.get("link", "")

                    published = parse_date(entry)

                    # GitHub Atom search results can expose the repository
                    # URL through the entry link.
                    if not url:
                        continue

                    mark_seen(
                        item_id=item_id,
                        url=url,
                        title=title,
                        published=published,
                    )

                    new_items += 1

                    if not send_notifications:
                        continue

                    # Rich Discord embed
                    embed = discord.Embed(
                        title=f"🚀  NEW AI REPOSITORY",
                        url=url,
                        description=(
                            f"### [{title[:180]}]({url})\n"
                            f"Repository baru yang terdeteksi dari GitHub.\n\n"
                            f"> 🔎 **Search:** `{query}`"
                        ),
                        color=discord.Color.from_rgb(88, 101, 242),
                        timestamp=datetime.now(timezone.utc),
                    )

                    # Try to extract owner/repository name for a cleaner card.
                    repo_name = title
                    if " - " in title:
                        repo_name = title.split(" - ", 1)[0].strip()

                    embed.add_field(
                        name="📦 Repository",
                        value=f"`{repo_name[:100]}`",
                        inline=True,
                    )

                    embed.add_field(
                        name="🕒 Published",
                        value=f"`{published}`",
                        inline=True,
                    )

                    embed.add_field(
                        name="🏷️ Category",
                        value="`AI / Developer Tools`",
                        inline=True,
                    )

                    embed.add_field(
                        name="🔗 Open Repository",
                        value=f"[**View on GitHub →**]({url})",
                        inline=False,
                    )

                    embed.set_author(
                        name="GitHub AI Repo Radar",
                        url="https://github.com/search?q=AI&type=repositories",
                    )

                    embed.set_thumbnail(
                        url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                    )

                    embed.set_footer(
                        text="GitHub RSS • AI Repo Radar • Automatic Discovery",
                        icon_url="https://github.githubassets.com/favicons/favicon.png",
                    )

                    await channel.send(
                        content="**🔔 New AI repository detected!**",
                        embed=embed,
                    )

                    # Avoid sending too quickly.
                    await asyncio.sleep(1)

            except Exception as exc:
                print(f"[RSS ERROR] {query}: {exc}")

            await asyncio.sleep(1)

    return new_items


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")

    if not github_scanner.is_running():
        github_scanner.start()


@tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
async def github_scanner():
    try:
        count = await scan_github()
        print(f"[SCAN] {count} new items")
    except Exception as exc:
        print(f"[SCAN ERROR] {exc}")


@github_scanner.before_loop
async def before_scanner():
    await bot.wait_until_ready()


@bot.tree.command(
    name="scan",
    description="Scan GitHub RSS sekarang."
)
async def scan_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    count = await scan_github()

    await interaction.followup.send(
        f"Scan selesai. `{count}` item baru ditemukan.",
        ephemeral=True,
    )


@bot.tree.command(
    name="feeds",
    description="Tampilkan keyword GitHub RSS yang dimonitor."
)
async def feeds_command(interaction: discord.Interaction):
    text = "\n".join(
        f"• `{query}`"
        for query in SEARCH_QUERIES
    )

    await interaction.response.send_message(
        f"**GitHub AI RSS feeds yang dimonitor:**\n{text}",
        ephemeral=True,
    )


@bot.tree.command(
    name="test",
    description="Test Discord notification."
)
async def test_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="GitHub RSS Bot",
        description="Discord notification berhasil.",
        color=discord.Color.green(),
    )

    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN belum diisi.")

    if CHANNEL_ID == 0:
        raise RuntimeError("DISCORD_CHANNEL_ID belum diisi.")

    bot.run(DISCORD_TOKEN)
