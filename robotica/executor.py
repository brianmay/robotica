""" Robotica Schedule. """
import asyncio
from typing import Dict, Any, Set  # NOQA
import logging

import yaml

from robotica.lifx import Lifx
from robotica.audio import Audio

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

    def is_action_required_for_locations(self, execute: Action) -> bool:
        locations = set(execute['locations'])

        lights = None
        message = None
        music = None

        if self._lifx.is_action_required_for_locations(locations):

            if 'lights' in execute:
                lights = execute['lights']

        if self._audio.is_action_required_for_locations(locations):

            if 'message' in execute:
                message = execute['message']

            if 'music' in execute:
                music = execute['music']

        return any([lights, message, music])

    async def _do_lights(self, locations: Set[str], execute: Dict[str, Any]) -> None:
        if 'lights' in execute:
            lights = execute['lights']
            lifx = self._lifx

            action = lights['action']
            if action == "flash":
                await lifx.flash(locations=locations)
            elif action == "wake_up":
                await lifx.wake_up(locations=locations)
            else:
                logger.error("Unknown action '%s'.", action)

    async def _do_audio(self, locations: Set[str], execute: Dict[str, Any]) -> None:
        if 'message' in execute:
            message = execute['message']
            audio = self._audio

            await audio.say(
                locations=locations,
                text=message['text'])

        if 'music' in execute:
            music = execute['music']
            audio = self._audio

            await audio.music_play(
                locations=locations,
                play_list=music['play_list'])

    async def do_action(self, action: Dict[str, Any]) -> None:
        locations = set(action['locations'])

        await asyncio.gather(
            self._do_lights(locations, action),
            self._do_audio(locations, action),
            loop=self._loop
        )
