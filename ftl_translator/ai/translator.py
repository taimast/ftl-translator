import logging
from typing import Protocol, Sequence

import httpx
from openai import AsyncOpenAI
from openai.types import Batch, ChatModel
from openai.types.chat import ChatCompletionMessageParam

from ftl_translator.options import Locale

from .batch_job import (
    create_batch_file,
    create_batch_job,
    parse_batch_content,
    while_get_batch_content,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a translation assistant for ftl files. "
    "I will send you plain text or text from ftl files with variables and text. "
    "Please translate the following text from {source_language} to {target_language}, "
    "keeping the original tags and variables (e.g., HTML or XML) unchanged. "
    "Send only the translated text, without introductions."
)


class TranslateObj(Protocol):
    data: str
    source_locale: Locale
    target_locale: Locale
    translated_data: str = ""


class AiTranslator:
    def __init__(
        self,
        api_key: str,
        model: ChatModel = "gpt-4o-mini",
        system_prompt: str = SYSTEM_PROMPT,
        source: str = "ru",
        target: str = "en",
        check_interval: int = 10,
        proxy: str | None = None,
    ):
        self.source = source
        self.target = target
        self.check_interval = check_interval

        self.system_prompt = system_prompt
        self.model: ChatModel = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            http_client=httpx.AsyncClient(proxies=proxy),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()

    def create_promps(
        self,
        batch: Sequence[TranslateObj],
    ) -> list[list[ChatCompletionMessageParam]]:
        prompts = []
        for obj in batch:
            system_prompt = self.system_prompt.format(
                source_language=obj.source_locale,
                target_language=obj.target_locale,
            )
            prompts.append(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": obj.data},
                ]
            )
        return prompts

    async def create_translate_batch(
        self,
        batch: Sequence[TranslateObj],
    ) -> Batch:
        prompts = self.create_promps(batch)
        batch_file = create_batch_file(prompts, self.model)
        batch_job = await create_batch_job(self.client, self.model, batch_file)
        return batch_job

    async def translate_batch[T: TranslateObj](
        self,
        batch: Sequence[T],
    ) -> Sequence[T]:
        batch_job = await self.create_translate_batch(batch)
        batch_content = await while_get_batch_content(
            self.client,
            batch_job.id,
            self.check_interval,
        )
        results = await parse_batch_content(batch_content)

        for i, obj in enumerate(batch):
            obj.translated_data = results[i]

        return batch
