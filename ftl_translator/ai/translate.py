from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import aiofiles
from openai.types import ChatModel

from ..options import BaseTranslateOpts, Locale, parse_ftl_files
from .translator import SYSTEM_PROMPT, AiTranslator

logger = logging.getLogger(__name__)


class AiTranslateOpts(BaseTranslateOpts):
    api_key: str
    model: ChatModel = "gpt-4o-mini"
    system_prompt: str = SYSTEM_PROMPT
    source: str = "ru"
    target: str = "en"
    check_interval: int = 10
    proxy: str | None = None


@dataclass
class TranslateObj:
    data: str
    source_locale: Locale
    target_locale: Locale
    target_file: Path
    translated_data: str = ""


async def translate(opts: AiTranslateOpts):
    ftl_files = parse_ftl_files(opts.origin_locale_dir)

    async with AiTranslator(
        api_key=opts.api_key,
        model=opts.model,
        system_prompt=opts.system_prompt,
        source=opts.source,
        target=opts.target,
        check_interval=opts.check_interval,
        proxy=opts.proxy,
    ) as a_translator:
        translate_objs: list[TranslateObj] = []
        for target_locale in opts.target_locales:
            logger.info(f"[{opts.origin_locale} -> {target_locale}] Translating...")

            for file in ftl_files:
                if not opts.is_applicable(file):
                    continue

                target_file = opts.create_target_file(file, target_locale)
                logger.debug(f"Translating {file.name}")

                file_text = file.read_text(encoding="utf-8")

                translate_obj = TranslateObj(
                    data=file_text,
                    target_file=target_file,
                    source_locale=opts.origin_locale,
                    target_locale=target_locale,
                )
                translate_objs.append(translate_obj)

        translated_batch = await a_translator.translate_batch(translate_objs)
        for obj in translated_batch:
            async with aiofiles.open(obj.target_file, "w", encoding="utf-8") as f:
                await f.write(obj.translated_data)

            logger.info(
                f"[{obj.source_locale} -> {obj.target_locale}] Translation saved to {obj.target_file}"
            )

    logger.info("Translation completed")
