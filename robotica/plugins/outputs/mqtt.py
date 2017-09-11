""" Give verbal message. """
import asyncio
import json
import logging
from typing import Dict

from hbmqtt.client import MQTTClient, ClientException, QOS_0

from robotica.plugins.outputs import Output
from robotica.types import JsonType, Action, Config

logger = logging.getLogger(__name__)


class MqttOutput(Output):

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

        return True

    async def execute(self, location: str, action: Action) -> None:
        if not self.is_action_required_for_location(location, action):
            return

        await self._execute(
            '/action/%s/' % location,
            action,
        )

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
