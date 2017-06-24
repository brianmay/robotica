""" Give verbal message. """
import asyncio
import logging


logger = logging.getLogger(__name__)


class Message:

    def __init__(self, loop: asyncio.AbstractEventLoop, say_path: str):
        self._loop = loop
        self._say_path = say_path

    async def say(self, text: str):
        process = await asyncio.create_subprocess_exec(self._say_path, text)
        await process.wait()
