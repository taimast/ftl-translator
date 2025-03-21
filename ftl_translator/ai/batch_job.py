# Author: Viet Dac Lai
import asyncio
import io
import json
import logging
from pprint import pformat
from typing import Required, TypedDict

from openai import AsyncOpenAI
from openai.types import Batch, ChatModel
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from typing_extensions import NotRequired

logger = logging.getLogger(__name__)


class HasPrompt(TypedDict):
    system_prompt: NotRequired[str]
    prompt: Required[str]


# Асинхронная функция для парсинга JSONL контента
def parse_jsonl(content: bytes) -> list[dict]:
    data_list = []
    # Декодируем байты в строки и разбиваем на отдельные строки
    lines = content.decode("utf-8").splitlines()

    for line in lines:
        # Парсим каждую строку как JSON
        data = json.loads(line)
        data_list.append(data)

    return data_list


def write_to_jsonl(data_list: list[dict], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        for data in data_list:
            # Сериализуем каждый объект как JSON строку и записываем в файл
            json_str = json.dumps(data)
            f.write(json_str + "\n")


def create_batch_file(
    messages_batch: list[list[ChatCompletionMessageParam]],
    model: ChatModel,
) -> io.BytesIO:
    tasks = []
    for index, messages in enumerate(messages_batch, 1):
        task = {
            "custom_id": f"id-{index}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                # "response_format": {
                #     "type": "json_object"
                # },
                "messages": messages,
            },
        }

        tasks.append(task)

    io_file = io.BytesIO()
    for task in tasks:
        io_file.write(json.dumps(task).encode() + b"\n")

    return io_file


async def create_batch_job(
    client: AsyncOpenAI,
    model: ChatModel,
    io_file: io.BytesIO,
) -> Batch:
    batch_file = await client.files.create(
        file=io_file,
        purpose="batch",
    )

    batch_job = await client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "model": model,
            "purpose": "translate",
            "task": "header and introduction",
        },
    )
    logger.info(f"Batch job created: {batch_job.id}")
    return batch_job


async def while_get_batch_content(
    client,
    batch_job_id: str,
    interval: int = 10,
) -> bytes:
    while True:
        batch_job = await client.batches.retrieve(batch_job_id)
        logger.info(pformat(batch_job.model_dump()))
        if batch_job.status == "completed":
            result_file_id = batch_job.output_file_id
            result = await client.files.content(result_file_id)
            content = result.content
            return content

        await asyncio.sleep(interval)


async def parse_batch_content(content: bytes) -> list[str]:
    data_list = parse_jsonl(content)
    results = []
    for data in data_list:
        data_result = data["response"]["body"]["choices"][0]["message"]["content"]
        results.append(data_result)
    return results
