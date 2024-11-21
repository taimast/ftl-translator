import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from fluent.syntax import parse
import logging

from ftl_translator.extractor import MessageInfo
from ftl_translator.translator import GoogleTranslator
import aiofiles

logger = logging.getLogger(__name__)


class Locale(StrEnum):
    """Language codes."""

    ENGLISH = "en"
    RUSSIAN = "ru"

    ARAB = "ar"
    CHINESE = "zh-CN"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    INDIAN = "hi"
    JAPANESE = "ja"
    PORTUGUESE = "pt"
    TURKISH = "tr"
    UKRAINIAN = "uk"

    PHILIPPINE = "tl"
    INDONESIAN = "id"


@dataclass
class TranslateOpts:
    locales_dir: Path
    origin_locale: Locale = Locale.RUSSIAN
    target_locales: list[Locale] = field(default_factory=lambda: list(Locale))
    include_files: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)

    include_variables: list[str] = field(default_factory=list)
    exclude_variables: list[str] = field(default_factory=list)

    batch_size: int = 5
    limit_translate: int = 4

    origin_locale_dir: Path = field(init=False)

    def __post_init__(self):
        self.target_locales = list(
            set(filter(lambda x: x != self.origin_locale, self.target_locales))
        )
        self.origin_locale_dir = Path(self.locales_dir, self.origin_locale)

    # подходит ли под критерии
    def is_applicable(self, file: Path) -> bool:
        if self.include_files and file.name not in self.include_files:
            return False
        if self.exclude_files and file.name in self.exclude_files:
            return False
        return True

    def create_target_file(self, file: Path, target_locale: str) -> Path:
        try:
            # Create a relative path from the origin locale directory
            relative_path = file.relative_to(self.origin_locale_dir)
        except ValueError:
            # If the file is not in the origin locale directory, raise an error
            raise ValueError(
                f"{file} is not in the subpath of {self.origin_locale_dir}"
            )

        # Construct new path with target locale
        new_file = Path(self.locales_dir, target_locale, relative_path)

        # Create parent directories if they don't exist
        new_file.parent.mkdir(parents=True, exist_ok=True)

        return new_file


def parse_ftl_files(locale_dir: Path) -> list[Path]:
    ftl_files = []
    for file in locale_dir.iterdir():
        if file.is_file() and file.suffix == ".ftl":
            ftl_files.append(file)
        else:
            ftl_files.extend(parse_ftl_files(file))
    return ftl_files


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
        translated_text = translated_batch[i]
        info.text = translated_text

    return msg_info_batch


async def translate(opts: TranslateOpts):
    ftl_files = parse_ftl_files(opts.origin_locale_dir)

    async with GoogleTranslator(
        source=opts.origin_locale,
        limit=opts.limit_translate,
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
                    messages_info[i : i + opts.batch_size]
                    for i in range(0, len(messages_info), opts.batch_size)
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
