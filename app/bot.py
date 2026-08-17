import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .config import Settings
from .db import Database
from .github import GitHubClient
from .scoring import Scorer
from .formatter import build_embed
from .llm import OllamaAnalyzer


log = logging.getLogger(__name__)


class RadarBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

        self.settings = settings
        self.db = Database(settings.database_path)
        self.scorer = Scorer(settings.categories, settings.negative_keywords)
        self.llm = (
            OllamaAnalyzer(settings.ollama_base_url, settings.ollama_model)
            if settings.enable_llm
            else None
        )
        self.scan_lock = asyncio.Lock()
        self.ready_once = False

    async def setup_hook(self):
        self.tree.add_command(ScanCommand(self))
        self.tree.add_command(StatsCommand(self))
        self.tree.add_command(LatestCommand(self))
        self.tree.add_command(TestCommand(self))

        await self.tree.sync()
        self.scanner.start()

    async def on_ready(self):
        log.info("Logged in as %s (%s)", self.user, self.user.id)
        if not self.ready_once:
            self.ready_once = True

    @tasks.loop(minutes=10)
    async def scanner(self):
        try:
            await self.scan()
        except Exception:
            log.exception("Scheduled scan failed.")

    @scanner.before_loop
    async def before_scanner(self):
        await self.wait_until_ready()
        self.scanner.change_interval(
            minutes=self.settings.poll_interval_minutes
        )

    async def scan(self) -> int:
        if self.scan_lock.locked():
            log.warning("Scan already running; skipping.")
            return 0

        async with self.scan_lock:
            channel = self.get_channel(self.settings.discord_channel_id)
            if channel is None:
                channel = await self.fetch_channel(self.settings.discord_channel_id)

            notified = 0

            async with GitHubClient(self.settings.github_token) as gh:
                for query in self.settings.queries:
                    if notified >= self.settings.max_notifications_per_cycle:
                        break

                    repos = await gh.search_repositories(
                        query=query,
                        lookback_hours=self.settings.initial_lookback_hours,
                        per_page=self.settings.max_results_per_query,
                    )

                    # Serial requests are intentional to be gentle on API limits.
                    for repo in repos:
                        if notified >= self.settings.max_notifications_per_cycle:
                            break

                        if self.db.exists(repo["id"]):
                            continue

                        score, category, reason = self.scorer.score(repo)
                        self.db.insert(repo, category, score, reason)

                        if score < self.settings.min_score_to_notify:
                            continue

                        llm_result = None
                        if self.llm:
                            try:
                                llm_result = await self.llm.analyze(
                                    repo, category, score
                                )
                            except Exception:
                                log.exception(
                                    "LLM analysis failed for %s", repo["full_name"]
                                )

                        embed = build_embed(
                            repo, category, score, reason, llm_result
                        )
                        await channel.send(embed=embed)
                        self.db.mark_notified(repo["id"])
                        notified += 1

                        await asyncio.sleep(1)

            log.info("Scan complete. Notifications: %d", notified)
            return notified


class BaseCommand:
    def __init__(self, bot: RadarBot):
        self.bot = bot


class ScanCommand(app_commands.Command):
    def __init__(self, bot: RadarBot):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            count = await bot.scan()
            await interaction.followup.send(
                f"Scan selesai. `{count}` repository baru dikirim.",
                ephemeral=True,
            )

        super().__init__(
            name="scan",
            description="Jalankan scan GitHub sekarang.",
            callback=callback,
        )


class StatsCommand(app_commands.Command):
    def __init__(self, bot: RadarBot):
        async def callback(interaction: discord.Interaction):
            stats = bot.db.stats()
            await interaction.response.send_message(
                f"**AI Repo Radar Stats**\n"
                f"Repositories ditemukan: `{stats['total']}`\n"
                f"Sudah dinotifikasi: `{stats['notified']}`\n"
                f"Average score: `{stats['avg_score']}`",
                ephemeral=True,
            )

        super().__init__(
            name="stats",
            description="Lihat statistik repository yang ditemukan.",
            callback=callback,
        )


class LatestCommand(app_commands.Command):
    def __init__(self, bot: RadarBot):
        async def callback(interaction: discord.Interaction):
            rows = bot.db.latest(10)
            if not rows:
                text = "Belum ada repository."
            else:
                lines = []
                for r in rows:
                    lines.append(
                        f"**{r['full_name']}** — `{r['score']}/100` "
                        f"`{r['category']}`\n{r['url']}"
                    )
                text = "\n\n".join(lines)

            await interaction.response.send_message(
                text[:2000], ephemeral=True
            )

        super().__init__(
            name="latest",
            description="Tampilkan 10 repository terakhir.",
            callback=callback,
        )


class TestCommand(app_commands.Command):
    def __init__(self, bot: RadarBot):
        async def callback(interaction: discord.Interaction):
            embed = discord.Embed(
                title="AI Repo Radar",
                description="Discord notification test berhasil.",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Status",
                value="Bot online dan dapat mengirim embed.",
                inline=False,
            )
            await interaction.response.send_message(embed=embed)

        super().__init__(
            name="test",
            description="Tes Discord notification.",
            callback=callback,
        )
