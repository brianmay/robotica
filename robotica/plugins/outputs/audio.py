""" Give verbal message. """
import asyncio
import logging
import shlex
from typing import Dict, List

from robotica.plugins.outputs import Output
from robotica.types import Action, Config

logger = logging.getLogger(__name__)


class AudioOutput(Output):

    def __init__(
            self, *,
            name: str,
            loop: asyncio.AbstractEventLoop,
            config: Config) -> None:
        super().__init__(
            name=name,
            loop=loop,
            config=config,
        )
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

        if 'sound' in action:
            return True

        if 'message' in action:
            return True

        if 'music' in action:
            return True

        return False

    async def execute(self, location: str, action: Action) -> None:
        location_config = self._locations.get(location, {})
        music_pause_cmd = location_config.get('music_pause_cmd', [])
        music_resume_cmd = location_config.get('music_resume_cmd', [])

        # Stop music if requested otherwise pause music.
        if 'music' in action and action['music'] is None:
            await self.music_stop(location=location)
            paused = False
        else:
            paused = await self._execute(music_pause_cmd, {}) == 0

        # Play requested sound.
        if 'sound' in action and action['sound'] is not None:
            sound = action['sound']
            await self.play_sound(
                location=location,
                sound=sound['name'])

        # Play requested message.
        if 'message' in action:
            message = action['message']
            await self.say(
                location=location,
                text=message['text'])

        # Start requested music or resume if paused.
        if 'music' in action and action['music'] is not None:
            music = action['music']
            await self.music_play(
                location=location,
                play_list=music['play_list'])
        elif paused:
            await self._execute(music_resume_cmd, {})

    @staticmethod
    async def _execute(cmd_list: List[str], params: Dict[str, str]) -> int:
        for cmd in cmd_list:
            split = [
                value.format(**params) for value in shlex.split(cmd)
            ]
            logger.info("About to execute %s", split)
            process = await asyncio.create_subprocess_exec(*split)
            result = await process.wait()
            if result != 0:
                logger.info("Command %s returned %d", split, result)
                return result
        return 0

    async def say(self, location: str, text: str) -> None:
        location_config = self._locations.get(location, {})
        say_cmd = location_config.get('say_cmd', [])
        if len(say_cmd) == 0:
            return
        logger.debug("%s: About to say '%s'.", location, text)

        await self.play_sound(location, 'prefix')
        await self._execute(say_cmd, {'text': text})
        await self.play_sound(location, 'repeat')
        await self._execute(say_cmd, {'text': text})
        await self.play_sound(location, 'postfix')

    async def play_sound(self, location: str, sound: str) -> None:
        sound_file = self._config['sounds'].get(sound)
        if not sound_file:
            return
        location_config = self._locations.get(location, {})
        play_cmd = location_config.get('play_cmd', [])
        if len(play_cmd) == 0:
            return
        logger.debug("%s: About to play_sound sound '%s'.", location, sound_file)
        await self._execute(play_cmd, {'file': sound_file})

    async def music_play(self, location: str, play_list: str) -> None:
        location_config = self._locations.get(location, {})
        music_play_cmd = location_config.get('music_play_cmd', [])
        if len(music_play_cmd) == 0:
            return
        logger.debug("%s: About to play_sound music '%s'.", location, play_list)
        await self._execute(music_play_cmd, {'play_list': play_list})

    async def music_stop(self, location: str) -> None:
        location_config = self._locations.get(location, {})
        music_stop_cmd = location_config.get('music_stop_cmd', [])
        if len(music_stop_cmd) == 0:
            return
        logger.debug("%s: About to stop music.", location)
        await self._execute(music_stop_cmd, {})
