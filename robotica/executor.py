""" Robotica Schedule. """
import asyncio
import logging
from typing import Dict, Set, List, Optional  # NOQA
from typing import TYPE_CHECKING

from robotica.plugins.outputs import Output
from robotica.types import Action
if TYPE_CHECKING:
    from robotica.schedule import Scheduler  # NOQA

logger = logging.getLogger(__name__)


class Executor:
    def __init__(
            self, loop: asyncio.AbstractEventLoop, config: Dict) -> None:
        self._loop = loop
        self._config = config
        self._locations = config.get('locations', []) or []
        self._outputs = []  # type: List[Output]
        self._scheduler = None  # type: Optional['Scheduler']
        self._tasks = {}  # type: Dict[str, asyncio.Task[None]]
        self._queues = {}  # type: Dict[str, asyncio.Queue[Action]]

    def start(self) -> None:
        for location in self._locations:
            self._queues[location] = asyncio.Queue(loop=self._loop)
            self._tasks[location] = self._loop.create_task(
                self._process_queue(location)
            )

    def stop(self) -> None:
        for location in self._locations:
            self._tasks[location].cancel()
        for location in self._locations:
            try:
                self._loop.run_until_complete(self._tasks[location])
            except asyncio.CancelledError:
                pass

    def set_scheduler(self, scheduler: 'Scheduler') -> None:
        self._scheduler = scheduler

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

    async def _do_action(self, location: str, action: Action) -> None:

        coros = [
            output.execute(location, action)
            for output in self._outputs
        ]
        await asyncio.gather(
            *coros,
            loop=self._loop
        )

    async def _process_queue(self, location: str):
        assert location in self._queues
        while True:
            action = await self._queues[location].get()
            try:
                logger.info("Processing location %s action %s", location, action)
                await self._do_action(location, action)
            except Exception:
                logger.exception(
                    "Error occurred executing action for location %s", location)

    async def do_action(self, locations: Set[str], action: Action) -> None:
        required_locations = self.action_required_for_locations(locations, action)
        if len(required_locations) == 0:
            return

        for location in required_locations:
            if location in self._queues:
                await self._queues[location].put(action)

    async def do_actions(self, locations: Set[str], actions: List[Action]) -> None:
        for action in actions:
            await self.do_action(locations, action)
