""" Robotica Schedule. """
import asyncio
import logging
from typing import Dict, Any, Set, List  # NOQA

import yaml

from robotica.outputs import Output
from robotica.types import Action

logger = logging.getLogger(__name__)


class Executor:
    def __init__(
            self, loop: asyncio.AbstractEventLoop, config: Dict) -> None:
        self._loop = loop
        self._config = config
        self._outputs = []  # type: List[Output]
        self._lock = asyncio.Lock()

    def add_output(self, output: Output) -> None:
        self._outputs.append(output)

    def is_action_required_for_locations(
            self, locations: Set[str], action: Action) -> bool:

        action_required = [
            output.is_action_required_for_locations(locations, action)
            for output in self._outputs
        ]

        return any(action_required)

    async def do_action(self, locations: Set[str], action: Action) -> None:
        if self.is_action_required_for_locations(locations, action):
            with await self._lock:
                coros = [
                    output.execute(locations, action)
                    for output in self._outputs
                ]
                await asyncio.gather(
                    *coros,
                    loop=self._loop
                )

    async def do_actions(self, locations: Set[str], actions: List[Action]) -> None:
        for action in actions:
            await self.do_action(locations, action)
