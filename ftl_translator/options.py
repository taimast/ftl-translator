import logging
import typing
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, PrivateAttr

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


class BaseTranslateOpts(BaseModel):
    locales_dir: Path
    origin_locale: Locale = Locale.RUSSIAN
    target_locales: list[Locale] = field(default_factory=lambda: list(Locale))
    include_files: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)

    include_variables: list[str] = field(default_factory=list)
    exclude_variables: list[str] = field(default_factory=list)

    _origin_locale_dir: Path = PrivateAttr()

    def model_post_init(self, __context: typing.Any) -> None:
        self.target_locales = list(
            set(filter(lambda x: x != self.origin_locale, self.target_locales))
        )
        self._origin_locale_dir = Path(self.locales_dir, self.origin_locale)

    @property
    def origin_locale_dir(self) -> Path:
        return self._origin_locale_dir

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
