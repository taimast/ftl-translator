import asyncio
import logging
from typing import List

import aiohttp
from aiohttp_socks import ProxyConnector

logger = logging.getLogger(__name__)


class GoogleTranslatorError(Exception):
    def __init__(self, message):
        super().__init__(message)


class TooManyRequestsError(GoogleTranslatorError):
    def __init__(self):
        super().__init__("Too many requests")


class TranslationError(GoogleTranslatorError):
    def __init__(self, message):
        super().__init__(message)


class GoogleTranslator:
    """
    Class that uses Google Translate to translate text(s).
    """

    BASE_URL = "https://translate.google.com/translate_a/single"

    def __init__(
        self,
        source: str = "auto",
        target: str = "en",
        retry_wait_time: int = 5,
        retry_count: int = 3,
        limit: int = 10,
        proxies: list[str] | None = None,
    ):
        """
        Initialize the translator.
        @param source: source language to translate from
        @param target: target language to translate to
        @param proxies: proxies to be used for the requests
        """
        self.source = source
        self.target = target
        self.params = {
            "client": "gtx",
            "dt": "t",
            "sl": self.source,
            "tl": self.target,
            "q": "",
        }
        self.retry_wait_time = retry_wait_time
        self.retry_count = retry_count

        self.sessions: list[tuple[asyncio.Semaphore, aiohttp.ClientSession]] = []
        if proxies:
            for proxy in proxies:
                self.sessions.append(
                    (
                        asyncio.Semaphore(limit),
                        aiohttp.ClientSession(
                            connector=ProxyConnector.from_url(proxy),
                        ),
                    )
                )
        else:
            self.sessions.append((asyncio.Semaphore(limit), aiohttp.ClientSession()))

    async def close(self):
        for _, session in self.sessions:
            await session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def get_session(self) -> tuple[asyncio.Semaphore, aiohttp.ClientSession]:
        semaphore, session = self.sessions.pop(0)
        self.sessions.append((semaphore, session))
        return semaphore, session

    async def _request(self, params: dict) -> list:
        semaphore, session = self.get_session()

        async with semaphore:
            async with session.get(
                self.BASE_URL,
                params=params,
            ) as response:
                if response.status == 429:
                    raise TooManyRequestsError()
                elif not response.ok:
                    raise TranslationError(response.text)
                else:
                    result = await response.json()
                    if not result or not isinstance(result, list) or not result[0]:
                        raise TranslationError(
                            f"Translation not found: {await response.text()}"
                        )
                    return result[0]

    async def translate(
        self,
        text: str,
        source: str | None = None,
        target: str | None = None,
        retry_count: int | None = None,
    ) -> str:
        """
        Function to translate a text.
        @param text: desired text to translate
        @return: str: translated text
        """
        if not self._is_input_valid(text, max_chars=5000):
            raise ValueError("Invalid input: text is too long or empty.")

        params = self.params.copy()
        if source:
            params["sl"] = source
        if target:
            params["tl"] = target
        params["q"] = text.strip()

        try:
            items = await self._request(params)
            translated_text = "".join([item[0] for item in items if item[0]])

            logger.debug(
                f"[{params["sl"]} -> {params["tl"]}] Translated: {text} -> {translated_text}"
            )

            return translated_text
        except TooManyRequestsError as e:
            if retry_count is None:
                retry_count = self.retry_count
            else:
                retry_count -= 1

            if retry_count < 0:
                raise e

            logger.warning(
                f"Too many requests. Please try again later. Retry count: {retry_count}. "
                f"Retry wait time: {self.retry_wait_time}"
            )
            await asyncio.sleep(self.retry_wait_time)
            return await self.translate(
                text,
                source,
                target,
                retry_count=retry_count,
            )

    async def translate_file(self, path: str) -> str:
        """
        Translate text from a file.
        @param path: path to the target file
        @return: str: translated text
        """
        try:
            with open(path, "r", encoding="utf-8") as file:
                text = file.read()
            return await self.translate(text)
        except FileNotFoundError:
            raise Exception(f"File {path} not found.")
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")

    async def translate_batch(
        self,
        batch: List[str],
        source: str | None = None,
        target: str | None = None,
    ) -> List[str]:
        """
        Translate a list of texts.
        @param batch: list of texts to translate
        @return: list of translations
        """
        return await asyncio.gather(
            *(self.translate(text, source=source, target=target) for text in batch)
        )

    def _is_input_valid(self, text: str, max_chars: int = 5000) -> bool:
        """
        Check if the input is valid.
        @param text: input text
        @param max_chars: maximum length of the text
        @return: bool: True if text is valid
        """
        return bool(text and isinstance(text, str) and len(text) <= max_chars)
