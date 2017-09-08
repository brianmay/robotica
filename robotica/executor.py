""" Robotica Schedule. """
import asyncio
import logging
from typing import Dict, Set, List  # NOQA

from robotica.plugins.outputs import Output
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

    def action_required_for_locations(
            self, locations: Set[str], action: Action) -> Set[str]:

        required_locations = set([
            location
            for output in self._outputs
            for location in locations
            if output.is_action_required_for_location(location, action)
        ])

        return required_locations

    async def do_action(self, locations: Set[str], action: Action) -> None:
        required_locations = self.action_required_for_locations(locations, action)
        if len(required_locations) == 0:
            return

        with await self._lock:
            coros = [
                output.execute(location, action)
                for output in self._outputs
                for location in locations
            ]
            await asyncio.gather(
                *coros,
                loop=self._loop
            )

    async def do_actions(self, locations: Set[str], actions: List[Action]) -> None:
        for action in actions:
            await self.do_action(locations, action)
