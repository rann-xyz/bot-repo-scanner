import asyncio
import logging

from app.config import Settings
from app.bot import RadarBot


def main() -> None:
    settings = Settings.load()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = RadarBot(settings)
    asyncio.run(bot.start(settings.discord_token))


if __name__ == "__main__":
    main()
