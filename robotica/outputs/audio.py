""" Give verbal message. """
import asyncio
import logging
import shlex
from typing import Dict, List, Set

from robotica.outputs import Output
from robotica.types import Action

logger = logging.getLogger(__name__)


class AudioOutput(Output):

    def __init__(self, loop: asyncio.AbstractEventLoop, config: Dict) -> None:
        self._loop = loop
        self._config = config
        self._disabled = self._config['disabled']
        self._locations = self._config.get('locations', {}) or {}

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def is_action_required_for_location(self, location: str, action: Action) -> bool:
        if self._disabled:
            return False

        if location not in self._locations:
            return False

        if 'message' in action:
            return True

        if 'music' in action:
            return True

        return False

    async def execute(self, location: str, action: Action) -> None:
        if 'message' in action:
            message = action['message']

            await self.say(
                location=location,
                text=message['text'])

        if 'music' in action:
            music = action['music']

            await self.music_play(
                location=location,
                play_list=music['play_list'])

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

    async def say(self, location: str, text: str) -> None:
        location_config = self._locations.get(location, {})
        say_cmd = location_config.get('say_cmd', [])
        if len(say_cmd) == 0:
            return
        logger.debug("%s: About to say '%s'.", location, text)
        await self.music_stop(location)
        await self.play(location, 'prefix')
        await self._execute(say_cmd, {'text': text})
        await self.play(location, 'repeat')
        await self._execute(say_cmd, {'text': text})
        await self.play(location, 'postfix')

    async def play(self, location: str, sound: str) -> None:
        sound_file = self._config['sounds'].get(sound)
        if not sound_file:
            return
        location_config = self._locations.get(location, {})
        play_cmd = location_config.get('play_cmd', [])
        if len(play_cmd) == 0:
            return
        logger.debug("%s: About to play sound '%s'.", location, sound_file)
        await self._execute(play_cmd, {'file': sound_file})

    async def music_play(self, location: str, play_list: str) -> None:
        location_config = self._locations.get(location, {})
        music_play_cmd = location_config.get('music_play_cmd', [])
        if len(music_play_cmd) == 0:
            return
        logger.debug("%s: About to play music '%s'.", location, play_list)
        await self._execute(music_play_cmd, {'play_list': play_list})

    async def music_stop(self, location: str) -> None:
        location_config = self._locations.get(location, {})
        music_stop_cmd = location_config.get('music_stop_cmd', [])
        if len(music_stop_cmd) == 0:
            return
        logger.debug("%s: About to stop music.", location)
        await self._execute(music_stop_cmd, {})
