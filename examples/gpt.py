import asyncio
import logging
import os
from pathlib import Path

from ftl_translator.ai.translate import AiTranslateOpts, translate
from ftl_translator.options import Locale

logging.basicConfig(level=logging.DEBUG)

BASE_DIR = Path(__file__).parent
LOCALES_DIR = BASE_DIR / "locales"


async def main():
    opts = AiTranslateOpts(
        api_key=os.environ["OPENAI_API_KEY"],
        locales_dir=LOCALES_DIR,
        origin_locale=Locale.RUSSIAN,
        target_locales=[Locale.ENGLISH, Locale.CHINESE],
    )
    await translate(opts)


if __name__ == "__main__":
    asyncio.run(main())
