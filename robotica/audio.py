""" Give verbal message. """
import asyncio
import logging
import shlex
from typing import Dict, List, Set

import yaml

logger = logging.getLogger(__name__)


class Audio:

    def __init__(self, loop: asyncio.AbstractEventLoop, config: str) -> None:
        self._loop = loop
        with open(config, "r") as file:
            self._config = yaml.safe_load(file)
        self._disabled = self._config['disabled']
        self._location = self._config.get('location')

    def is_action_required_for_locations(self, locations: Set[str]) -> bool:
        if self._disabled:
            return False

        good_locations = [
            location
            for location in locations
            if location in self._location
        ]

        return len(good_locations) > 0

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

    async def _say(self, location: str, text: str) -> None:
        logger.debug("%s: About to consider say '%s'.", location, text)
        location_config = self._location.get(location, {})
        say_cmd = location_config.get('say_cmd', [])
        if len(say_cmd) == 0:
            return
        logger.debug("%s: About to say '%s'.", location, text)
        await self._music_stop(location)
        await self._play(location, 'prefix')
        await self._execute(say_cmd, {'text': text})
        await self._play(location, 'repeat')
        await self._execute(say_cmd, {'text': text})
        await self._play(location, 'postfix')

    async def say(self, locations: Set[str], text: str) -> None:
        if self._disabled:
            return
        coros = [
            self._say(location, text)
            for location in locations
        ]
        await asyncio.gather(*coros, loop=self._loop)

    async def _play(self, location: str, sound: str) -> None:
        sound_file = self._config['sounds'].get(sound)
        if not sound_file:
            return
        location_config = self._location.get(location, {})
        play_cmd = location_config.get('play_cmd', [])
        if len(play_cmd) == 0:
            return
        logger.debug("%s: About to play sound '%s'.", location, sound_file)
        await self._execute(play_cmd, {'file': sound_file})

    async def play(self, locations: Set[str], sound: str) -> None:
        if self._disabled:
            return
        coros = [
            self._play(location, sound)
            for location in locations
        ]
        await asyncio.gather(*coros, loop=self._loop)

    async def _music_play(self, location: str, play_list: str) -> None:
        location_config = self._location.get(location, {})
        music_play_cmd = location_config.get('music_play_cmd', [])
        if len(music_play_cmd) == 0:
            return
        logger.debug("%s: About to play music '%s'.", location, play_list)
        await self._execute(music_play_cmd, {'play_list': play_list})

    async def music_play(self, locations: Set[str], play_list: str) -> None:
        if self._disabled:
            return
        coros = [
            self._music_play(location, play_list)
            for location in locations
        ]
        await asyncio.gather(*coros, loop=self._loop)

    async def _music_stop(self, location: str) -> None:
        location_config = self._location.get(location, {})
        music_stop_cmd = location_config.get('music_stop_cmd', [])
        if len(music_stop_cmd) == 0:
            return
        logger.debug("%s: About to stop music.", location)
        await self._execute(music_stop_cmd, {})

    async def music_stop(self, locations: Set[str]) -> None:
        if self._disabled:
            return
        coros = [
            self._music_stop(location)
            for location in locations
        ]
        await asyncio.gather(*coros, loop=self._loop)
