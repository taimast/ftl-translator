import logging

import aiofiles
from fluent.syntax import parse

from ..extractor import MessageInfo
from ..options import BaseTranslateOpts, Locale, parse_ftl_files
from .translator import GoogleTranslator

logger = logging.getLogger(__name__)


class GoogleTranslateOpts(BaseTranslateOpts):
    translate_batch_size: int = 5
    translate_limit: int = 4
    translate_retry_wait_time: int = 5
    translate_retry_count: int = 3


async def translate_batch(
    msg_info_batch: list[MessageInfo],
    g_translator: GoogleTranslator,
    target_locale: Locale,
) -> list[MessageInfo]:
    batch_text = [info.text for info in msg_info_batch]

    translated_batch = await g_translator.translate_batch(
        batch_text, target=target_locale
    )
    for i, info in enumerate(msg_info_batch):
        translated_text = translated_batch[i]
        info.text = translated_text

    return msg_info_batch


async def translate_concatenated_batch(
    msg_info_batch: list[MessageInfo],
    g_translator: GoogleTranslator,
    target_locale: Locale,
) -> list[MessageInfo]:
    # какой то знак для разделения сообщений. Уникальный
    separator = "\n[◙]\n"
    batch_text = separator.join([info.text for info in msg_info_batch])

    translated_batch = await g_translator.translate(batch_text, target=target_locale)
    logger.debug(f"{batch_text} -> {translated_batch}")

    translated_batch = translated_batch.split(separator)

    for i, info in enumerate(msg_info_batch):
        try:
            translated_text = translated_batch[i]
        except IndexError:
            logger.warning(f"{batch_text} -> {translated_batch}")
            raise
        info.text = translated_text
    return msg_info_batch


async def translate(opts: GoogleTranslateOpts):
    ftl_files = parse_ftl_files(opts.origin_locale_dir)

    async with GoogleTranslator(
        source=opts.origin_locale,
        retry_wait_time=opts.translate_retry_wait_time,
        retry_count=opts.translate_retry_count,
        limit=opts.translate_limit,
    ) as g_translator:
        for target_locale in opts.target_locales:
            logger.info(f"[{opts.origin_locale} -> {target_locale}] Translating...")

            for file in ftl_files:
                if not opts.is_applicable(file):
                    continue
                target_file = opts.create_target_file(file, target_locale)
                logger.debug(f"Translating {file.name}")

                file_text = file.read_text(encoding="utf-8")
                resource = parse(file_text)
                messages_info = MessageInfo.get_message_info(resource)

                batches = [
                    messages_info[i : i + opts.translate_batch_size]
                    for i in range(0, len(messages_info), opts.translate_batch_size)
                ]

                translated_text = ""
                for batch in batches:
                    translated_batch = await translate_concatenated_batch(
                        batch, g_translator, target_locale
                    )
                    logger.debug(f"Batch size: {len(translated_batch)} translated")

                    for info in translated_batch:
                        translated_text += info.to_fluent()
                        translated_text += "\n\n"

                async with aiofiles.open(target_file, "w", encoding="utf-8") as f:
                    await f.write(translated_text)

                logger.info(
                    f"[{opts.origin_locale} -> {target_locale}] Translated {file.name}"
                )
    logger.info("Translation completed")
