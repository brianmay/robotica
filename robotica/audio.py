""" Give verbal message. """
import asyncio
import logging
import shlex
from typing import Dict, List

import yaml

logger = logging.getLogger(__name__)


class Audio:

    def __init__(self, loop: asyncio.AbstractEventLoop, config: str) -> None:
        self._loop = loop
        with open(config, "r") as file:
            self._config = yaml.safe_load(file)
        self._say_cmd = self._config.get('say_cmd') or []
        self._play_cmd = self._config.get('play_cmd') or []
        self._music_play_cmd = self._config.get('music_play_cmd') or []
        self._music_stop_cmd = self._config.get('music_stop_cmd') or []

    @staticmethod
    async def _execute(cmd_list: List[str], params: Dict[str, str]) -> None:
        for cmd in cmd_list:
            split = [
                value.format(**params) for value in shlex.split(cmd)
            ]
            logger.info("About to execute %s", split)
            process = await asyncio.create_subprocess_exec(*split)
            result = await process.wait()
            if result != 0:
                logger.info("Command %s returned %d", split, result)

    async def say(self, text: str) -> None:
        await self.music_stop()
        await self.play('prefix')
        await self._execute(self._say_cmd, {'text': text})
        await self.play('repeat')
        await self._execute(self._say_cmd, {'text': text})
        await self.play('postfix')

    async def play(self, sound: str) -> None:
        sound_file = self._config['sounds'][sound]
        if sound_file:
            await self._execute(self._play_cmd, {'file': sound_file})

    async def music_play(self, play_list: str) -> None:
        await self._execute(self._music_play_cmd, {'play_list': play_list})

    async def music_stop(self) -> None:
        await self._execute(self._music_stop_cmd, {})
