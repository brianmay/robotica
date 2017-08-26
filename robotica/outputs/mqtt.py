""" Give verbal message. """
import asyncio
import json

from hbmqtt.client import MQTTClient, ClientException, QOS_0
import logging
from typing import Set
import yaml

from robotica.outputs import Output
from robotica.types import JsonType, Action

logger = logging.getLogger(__name__)


class MqttOutput(Output):

    def __init__(self, loop: asyncio.AbstractEventLoop, config: str, client: MQTTClient) -> None:
        self._loop = loop
        with open(config, "r") as file:
            self._config = yaml.safe_load(file)
        self._disabled = self._config['disabled']
        self._location = self._config.get('location')
        self._client = client  # type: MQTTClient

    def is_action_required_for_locations(self, locations: Set[str], action: Action) -> bool:
        if self._disabled:
            return False

        good_locations = [
            location
            for location in locations
            if location in self._location
        ]

        if len(good_locations) == 0:
            return False

        if 'message' in action:
            return True

        if 'music' in action:
            return True

        return False

    async def execute(self, locations: Set[str], action: Action) -> None:
        if 'message' in action:
            message = action['message']

            await self.say(
                locations=locations,
                text=message['text'])

        if 'music' in action:
            music = action['music']

            await self.music_play(
                locations=locations,
                play_list=music['play_list'])

    async def _execute(self, topic: str, data: JsonType) -> None:
        logger.debug("About to publish %r to %s" % (data, topic))
        raw_data = json.dumps(data).encode('UTF8')
        try:
            await self._client.publish(
                topic,
                raw_data,
                qos=QOS_0,
            )
        except ClientException:
            logger.exception("The client operation failed.")

    async def _say(self, location: str, text: str) -> None:
        if location not in self._location:
            return
        logger.debug("%s: About to say '%s' (MQTT).", location, text)
        await self._execute(
            '/say/%s/' % location,
            text,
        )

    async def say(self, locations: Set[str], text: str) -> None:
        if self._disabled:
            return
        coros = [
            self._say(location, text)
            for location in locations
        ]
        await asyncio.gather(*coros, loop=self._loop)

    async def _play(self, location: str, sound: str) -> None:
        if location not in self._location:
            return
        logger.debug("%s: About to play sound '%s' (MQTT).", location, sound)
        await self._execute(
            '/play/%s/' % location,
            sound,
        )

    async def play(self, locations: Set[str], sound: str) -> None:
        if self._disabled:
            return
        coros = [
            self._play(location, sound)
            for location in locations
        ]
        await asyncio.gather(*coros, loop=self._loop)

    async def _music_play(self, location: str, play_list: str) -> None:
        if location not in self._location:
            return
        logger.debug("%s: About to play music '%s' (MQTT).", location, play_list)
        await self._execute(
            '/play_music/%s/' % location,
            play_list,
        )

    async def music_play(self, locations: Set[str], play_list: str) -> None:
        if self._disabled:
            return
        coros = [
            self._music_play(location, play_list)
            for location in locations
        ]
        await asyncio.gather(*coros, loop=self._loop)

    async def _music_stop(self, location: str) -> None:
        if location not in self._location:
            return
        logger.debug("%s: About to stop music (MQTT).", location)
        await self._execute(
            '/play_music/%s/' % location,
            None,
        )

    async def music_stop(self, locations: Set[str]) -> None:
        if self._disabled:
            return
        coros = [
            self._music_stop(location)
            for location in locations
        ]
        await asyncio.gather(*coros, loop=self._loop)
