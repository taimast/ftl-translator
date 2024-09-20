import asyncio
from logging import Logger
import logging
from pathlib import Path

from ftl_translator import Locale, TranslateOpts, translate

logging.basicConfig(level=logging.DEBUG)

BASE_DIR = Path(__file__).parent
LOCALES_DIR = BASE_DIR / "locales"


async def main():
    opts = TranslateOpts(
        locales_dir=LOCALES_DIR,
        origin_locale=Locale.ENGLISH,
        target_locales=[Locale.RUSSIAN, Locale.CHINESE],
    )
    await translate(opts)


if __name__ == "__main__":
    asyncio.run(main())
