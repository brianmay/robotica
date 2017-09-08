""" Give verbal message. """
import asyncio
import json
import logging
from typing import Dict

from hbmqtt.client import MQTTClient, ClientException, QOS_0

from robotica.plugins.outputs import Output
from robotica.types import JsonType, Action

logger = logging.getLogger(__name__)


class MqttOutput(Output):

    def __init__(self, loop: asyncio.AbstractEventLoop, config: Dict) -> None:
        self._loop = loop
        self._config = config
        self._disabled = self._config['disabled']
        self._broker_url = self._config['broker_url']
        self._locations = self._config.get('locations', {}) or {}
        self._client = MQTTClient()

    def start(self) -> None:
        if not self._disabled:
            self._loop.run_until_complete(self._client.connect(self._broker_url))

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

    async def say(self, location: str, text: str) -> None:
        if location not in self._locations:
            return
        logger.debug("%s: About to say '%s' (MQTT).", location, text)
        await self._execute(
            '/say/%s/' % location,
            text,
        )

    async def play(self, location: str, sound: str) -> None:
        if location not in self._locations:
            return
        logger.debug("%s: About to play sound '%s' (MQTT).", location, sound)
        await self._execute(
            '/play/%s/' % location,
            sound,
        )

    async def music_play(self, location: str, play_list: str) -> None:
        if location not in self._locations:
            return
        logger.debug("%s: About to play music '%s' (MQTT).", location, play_list)
        await self._execute(
            '/play_music/%s/' % location,
            play_list,
        )

    async def music_stop(self, location: str) -> None:
        if location not in self._locations:
            return
        logger.debug("%s: About to stop music (MQTT).", location)
        await self._execute(
            '/stop_music/%s/' % location,
            None,
        )
