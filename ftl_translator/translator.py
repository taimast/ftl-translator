import aiohttp
from typing import List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class GoogleTranslator:
    """
    Class that uses Google Translate to translate text(s).
    """

    BASE_URL = "https://translate.google.com/translate_a/single"

    def __init__(
        self,
        source: str = "auto",
        target: str = "en",
        proxy: Optional[str] = None,
        retry_wait_time: int = 5,
        retry_count: int = 3,
    ):
        """
        Initialize the translator.
        @param source: source language to translate from
        @param target: target language to translate to
        @param proxies: proxies to be used for the requests
        """
        self.source = source
        self.target = target
        self.proxy = proxy
        self.params = {
            "client": "gtx",
            "dt": "t",
            "sl": self.source,
            "tl": self.target,
            "q": "",
        }
        self.retry_wait_time = retry_wait_time
        self.retry_count = retry_count

        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """
        Create and enter an async context with aiohttp.ClientSession.
        """
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Close the aiohttp session when exiting the context.
        """
        if self.session:
            await self.session.close()
            self.session = None

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

        if not self.session:
            raise RuntimeError("Session is not initialized. Use 'async with' to create a session.")

        async with self.session.get(
            self.BASE_URL,
            params=params,
            proxy=self.proxy,
        ) as response:
            if response.status == 429:
                if retry_count is None:
                    retry_count = self.retry_count
                else:
                    retry_count -= 1

                if retry_count < 0:
                    raise Exception("Too many requests. Please try again later.")

                if retry_count > 0:
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

            if not response.ok:
                raise Exception(f"Request error: {response.status}")

            result = await response.json()

            if not result or not isinstance(result, list) or not result[0]:
                raise Exception("Translation error: translation not found.")

            translated_text = "".join([item[0] for item in result[0] if item[0]])

            logger.debug(
                f"[{params["sl"]} -> {params["tl"]}] Translated: {text} -> {translated_text}"
            )

            return translated_text

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
