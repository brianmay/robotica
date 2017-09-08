import asyncio
from typing import Dict

from robotica.executor import Executor
from robotica.plugins import Plugin
from robotica.schedule import Schedule
from robotica.types import Config


class Input(Plugin):
    def __init__(
            self, *,
            name: str,
            loop: asyncio.AbstractEventLoop,
            config: Config,
            executor: Executor,
            schedule: Schedule) -> None:
        super().__init__(name=name, loop=loop, config=config)
        self._executor = executor
        self._schedule = schedule
