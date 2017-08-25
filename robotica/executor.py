""" Robotica Schedule. """
import asyncio
import logging
from typing import Dict, Any, Set, List  # NOQA

import yaml

from robotica.outputs.audio import Audio
from robotica.outputs.lifx import Lifx

logger = logging.getLogger(__name__)


Action = Dict[str, Any]


class Executor:
    def __init__(
            self, loop: asyncio.AbstractEventLoop,
            config: str, lifx: Lifx, audio: Audio) -> None:
        self._loop = loop
        with open(config, "r") as file:
            self._config = yaml.safe_load(file)
        self._lifx = lifx
        self._audio = audio
        self._lock = asyncio.Lock()

    def is_action_required_for_locations(
            self, locations: Set[str], action: Action) -> bool:
        lights = None
        message = None
        music = None

        if self._lifx.is_action_required_for_locations(locations):

            if 'lights' in action:
                lights = action['lights']

        if self._audio.is_action_required_for_locations(locations):

            if 'message' in action:
                message = action['message']

            if 'music' in action:
                music = action['music']

        return any([lights, message, music])

    async def _do_lights(self, locations: Set[str], action: Action) -> None:
        if 'lights' in action:
            lights = action['lights']
            lifx = self._lifx

            lights_action = lights['action']
            if lights_action == "flash":
                await lifx.flash(locations=locations)
            elif lights_action == "wake_up":
                await lifx.wake_up(locations=locations)
            else:
                logger.error("Unknown action '%s'.", action)

    async def _do_audio(self, locations: Set[str], action: Action) -> None:
        if 'message' in action:
            message = action['message']
            audio = self._audio

            await audio.say(
                locations=locations,
                text=message['text'])

        if 'music' in action:
            music = action['music']
            audio = self._audio

            await audio.music_play(
                locations=locations,
                play_list=music['play_list'])

    async def do_action(self, locations: Set[str], action: Action) -> None:
        if self.is_action_required_for_locations(locations, action):
            with await self._lock:
                await asyncio.gather(
                    self._do_lights(locations, action),
                    self._do_audio(locations, action),
                    loop=self._loop
                )

    async def do_actions(self, locations: Set[str], actions: List[Action]) -> None:
        for action in actions:
            await self.do_action(locations, action)
