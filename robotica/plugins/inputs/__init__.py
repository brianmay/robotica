import asyncio
from typing import Optional

from robotica.executor import Executor
from robotica.plugins import Plugin
from robotica.schedule import Scheduler
from robotica.types import Config


class Input(Plugin):
    def __init__(
            self, *,
            name: str,
            loop: asyncio.AbstractEventLoop,
            config: Config,
            executor: Executor,
            scheduler: Optional[Scheduler]) -> None:
        super().__init__(name=name, loop=loop, config=config)
        self._executor = executor
        self._scheduler = scheduler
