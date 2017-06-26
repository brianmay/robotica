""" Give verbal message. """
import asyncio
import logging

import yaml

logger = logging.getLogger(__name__)


class Audio:

    def __init__(self, loop: asyncio.AbstractEventLoop, config: str):
        self._loop = loop
        with open(config, "r") as file:
            self._config = yaml.safe_load(file)
        self._say_path = self._config['say_path']

    async def say(self, text: str):
        process = await asyncio.create_subprocess_exec(self._say_path, text)
        await process.wait()
