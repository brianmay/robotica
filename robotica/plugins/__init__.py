import asyncio
import logging

from robotica.types import Config

logger = logging.getLogger(__name__)


class Plugin:
    def __init__(
            self, *,
            name: str,
            loop: asyncio.AbstractEventLoop,
            config: Config) -> None:
        super().__init__()
        self._name = name
        self._loop = loop
        self._config = config

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
