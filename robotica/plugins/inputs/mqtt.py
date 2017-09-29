import asyncio
import json
import logging
import platform
from typing import Any, Optional, Tuple, List

from hbmqtt.client import MQTTClient, ClientException, QOS_0

from robotica.executor import Executor
from robotica.plugins.inputs import Input
from robotica.schedule import Schedule
from robotica.types import Config, Action

logger = logging.getLogger(__name__)

JsonType = Any


class MqttInput(Input):
    def __init__(
            self, *,
            name: str,
            loop: asyncio.AbstractEventLoop,
            config: Config,
            executor: Executor,
            schedule: Optional[Schedule]) -> None:
        super().__init__(
            name=name,
            loop=loop,
            config=config,
            executor=executor,
            schedule=schedule,
        )
        self._disabled = self._config['disabled']
        self._broker_url = self._config['broker_url']
        self._locations = self._config.get('locations', []) or []
        self._task = None  # type: Optional[asyncio.Task]
        self._client = MQTTClient()

    def start(self) -> None:
        if not self._disabled:
            self._task = self._loop.create_task(self._mqtt())

    def stop(self) -> None:
        if not self._disabled and self._task is not None:
            self._task.cancel()
            try:
                self._loop.run_until_complete(self._task)
            except asyncio.CancelledError:
                pass

    def _get_topics(self) -> List[Tuple[str, int]]:
        if self._schedule is None:
            topics = [
                ('/action/%s/' % location, QOS_0)
                for location in self._locations
            ]
        else:
            topics = [
                ('/schedule/', QOS_0),
                ('/execute/', QOS_0),
            ]
        return topics

    async def _process_execute(self, data: JsonType) -> None:
        if self._schedule is None:
            return

        reply_topic = data.get('reply_topic', None)
        server = platform.node()

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
            await reply({'status': 'error', 'server': server, })
            return

        try:
            await reply({'status': 'processing', 'server': server, })
            await self._executor.do_actions(locations, actions)
            await reply({'status': 'success', 'server': server, })
        except Exception as e:
            logger.exception("Error in _execute")
            await reply({'status': 'error', 'server': server, })

        return

    async def _process_schedule(self, data: JsonType) -> None:
        if self._schedule is not None:
            await self._schedule.set_schedule(data)
            self._schedule.save_schedule()

    async def _process_action(self, location: str, action: Action) -> None:
        if self._schedule is None:
            await self._executor.do_action({location}, action)

    async def _process(self, topic: str, data: JsonType) -> None:
        logger.info("Received %s %s", topic, data)
        if topic.startswith("/execute/"):
            await self._process_execute(data)
        if topic.startswith("/schedule/"):
            await self._process_schedule(data)
        if topic.startswith("/action/"):
            location = topic[8:].rstrip("/")
            await self._process_action(location, data)

    async def _mqtt(self) -> None:
        client = self._client
        await client.connect(self._broker_url)
        await client.subscribe(self._get_topics())

        while True:
            try:
                message = await client.deliver_message()
                packet = message.publish_packet
                topic = packet.variable_header.topic_name
                raw_data = bytes(packet.payload.data).decode('UTF8')

                try:
                    data = json.loads(raw_data)
                    self._loop.create_task(self._process(topic, data))
                except json.JSONDecodeError as e:
                    logger.error("JSON Error %s" % e)

            except asyncio.CancelledError:
                topics = self._get_topics()
                await client.unsubscribe([t[0] for t in topics])
                await client.disconnect()
                raise
            except ClientException as e:
                logger.error("Client exception: %s" % e)
            except Exception as e:
                logger.exception("Unknown exception.")
