from dataclasses import dataclass
from pathlib import Path
import os

import yaml
from dotenv import load_dotenv


@dataclass
class Settings:
    discord_token: str
    discord_channel_id: int
    github_token: str
    poll_interval_minutes: int
    initial_lookback_hours: int
    max_results_per_query: int
    min_score_to_notify: int
    max_notifications_per_cycle: int
    database_path: str
    log_level: str
    enable_llm: bool
    ollama_base_url: str
    ollama_model: str
    categories: dict
    negative_keywords: list[str]
    queries: list[str]

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()

        token = os.getenv("DISCORD_TOKEN", "").strip()
        channel = os.getenv("DISCORD_CHANNEL_ID", "").strip()
        github = os.getenv("GITHUB_TOKEN", "").strip()

        if not token:
            raise RuntimeError("DISCORD_TOKEN belum diisi.")
        if not channel.isdigit():
            raise RuntimeError("DISCORD_CHANNEL_ID harus berupa integer Discord channel ID.")
        if not github:
            raise RuntimeError("GITHUB_TOKEN belum diisi.")

        cfg_path = Path("config.yaml")
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        return cls(
            discord_token=token,
            discord_channel_id=int(channel),
            github_token=github,
            poll_interval_minutes=max(5, int(os.getenv("POLL_INTERVAL_MINUTES", "10"))),
            initial_lookback_hours=max(1, int(os.getenv("INITIAL_LOOKBACK_HOURS", "24"))),
            max_results_per_query=max(1, min(100, int(os.getenv("MAX_RESULTS_PER_QUERY", "20")))),
            min_score_to_notify=int(os.getenv("MIN_SCORE_TO_NOTIFY", "55")),
            max_notifications_per_cycle=max(1, int(os.getenv("MAX_NOTIFICATIONS_PER_CYCLE", "10"))),
            database_path=os.getenv("DATABASE_PATH", "data/bot.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_llm=os.getenv("ENABLE_LLM", "false").lower() == "true",
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            categories=cfg.get("categories", {}),
            negative_keywords=cfg.get("negative_keywords", []),
            queries=cfg.get("queries", []),
        )
