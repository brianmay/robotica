""" Give verbal message. """
import asyncio
import logging
import shlex
from typing import Dict

import yaml

logger = logging.getLogger(__name__)


class Audio:

    def __init__(self, loop: asyncio.AbstractEventLoop, config: str) -> None:
        self._loop = loop
        with open(config, "r") as file:
            self._config = yaml.safe_load(file)
        self._say_cmd = self._config['say_cmd']
        self._play_cmd = self._config['play_cmd']

    @staticmethod
    async def execute(cmd: str, params: Dict[str, str]):
        split = [
            value.format(**params) for value in shlex.split(cmd)
        ]
        logger.info("About to execute %s", split)
        process = await asyncio.create_subprocess_exec(*split)
        await process.wait()

    async def say(self, text: str):
        await self.play('prefix')
        await self.execute(self._say_cmd, {'text': text})
        await self.play('repeat')
        await self.execute(self._say_cmd, {'text': text})
        await self.play('postfix')

    async def play(self, sound: str):
        sound_file = self._config['sounds'][sound]
        if sound_file:
            await self.execute(self._play_cmd, {'file': sound_file})
