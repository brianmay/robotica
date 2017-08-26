import asyncio
import json
import logging

import yaml

from typing import Any, Optional

from hbmqtt.client import MQTTClient, ClientException, QOS_0

from robotica.executor import Executor
from robotica.inputs import Input
from robotica.schedule import Schedule

logger = logging.getLogger(__name__)

JsonType = Any


class MqttInput(Input):
    def __init__(
            self, loop: asyncio.AbstractEventLoop,
            config: str,
            executor: Executor,
            schedule: Schedule,
            client: MQTTClient) -> None:
        self._loop = loop
        with open(config, "r") as file:
            self._config = yaml.safe_load(file)
        self._disabled = self._config['disabled']
        self._broker_url = self._config['broker_url']
        self._executor = executor
        self._schedule = schedule
        self._task = None  # type: Optional[asyncio.Task]
        self._client = client

    def start(self) -> None:
        if not self._disabled:
            self._task = self._loop.create_task(self._mqtt())

    def stop(self) -> None:
        if not self._disabled and self._task is not None:
            self._client.unsubscribe('/execute')
            self._task.cancel()
            try:
                self._loop.run_until_complete(self._task)
            except asyncio.CancelledError:
                pass

    async def _execute(self, data: JsonType) -> None:

        reply_topic = data.get('reply_topic', None)

        async def reply(data: JsonType) -> None:
            client = self._client
            raw_data = json.dumps(data).encode('UTF8')
            if reply_topic is not None:
                await client.publish(reply_topic, raw_data, qos=QOS_0)

        try:
            locations = data['locations']
            actions = data['actions']
        except KeyError:
            logger.error("Required value missing.")
            await reply({'status': 'error'})
            return

        try:
            await reply({'status': 'processing'})
            await self._executor.do_actions(locations, actions)
            await reply({'status': 'success'})
        except Exception as e:
            logger.exception("Error in _execute")
            await reply({'status': 'error'})

        return

    async def _process(self, topic: str, data: JsonType) -> None:
        if topic == "/execute":
            await self._execute(data)

    async def _mqtt(self) -> None:
        client = self._client
        await client.connect(self._broker_url)
        await client.subscribe([
            ('/execute', QOS_0),
        ])

        while True:
            try:
                message = await client.deliver_message()
                packet = message.publish_packet
                topic = packet.variable_header.topic_name
                raw_data = bytes(packet.payload.data).decode('UTF8')

                try:
                    data = json.loads(raw_data)
                    await self._process(topic, data)
                except json.JSONDecodeError as e:
                    logger.error("JSON Error %s" % e)

            except asyncio.CancelledError:
                await client.unsubscribe(['/execute'])
                await client.disconnect()
                raise
            except ClientException as e:
                logger.error("Client exception: %s" % e)
            except Exception as e:
                logger.exception("Unknown exception.")
