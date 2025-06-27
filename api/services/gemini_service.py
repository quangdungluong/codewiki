import os
from typing import AsyncGenerator

from google import genai
from google.genai import types

from utils.format_message import format_message


class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-2.5-flash"

    async def generate(
        self, system_prompt: str, data: dict
    ) -> AsyncGenerator[str, None]:
        user_message = format_message(data)
        try:
            async for chunk in await self.client.aio.models.generate_content_stream(
                model=self.model,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=12000,
                ),
                contents=user_message,
            ):
                yield chunk.text
        except Exception as e:
            raise (e)
