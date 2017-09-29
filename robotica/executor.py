""" Robotica Schedule. """
import asyncio
import time
import logging
from typing import Dict, Set, List, Optional  # NOQA
from typing import TYPE_CHECKING

import math

from robotica.plugins.outputs import Output
from robotica.types import Action
if TYPE_CHECKING:
    from robotica.schedule import Schedule  # NOQA

logger = logging.getLogger(__name__)


class Timer:

    def __init__(
            self, *,
            loop: asyncio.AbstractEventLoop,
            executor: 'Executor',
            locations: Set[str],
            name: str) -> None:
        self._loop = loop
        self._executor = executor
        self._locations = locations
        self._name = name
        self._timer_running = False

    @property
    def is_running(self) -> bool:
        return self._timer_running

    async def _error(self, message: str):
        logger.error('timer %s: %s', self._name, message)
        action = {
            'message': {'text': 'The timer %s %s' % (self._name, message)}
        }
        await self._executor.do_action(self._locations, action)

    async def _warn(
            self, *,
            time_left: int, time_total: int,
            epoch_minute: float,
            epoch_finish: float):
        logger.info(
            "timer warn %s: time left %d, time total %s",
            self._name, time_left, time_total)

        action = {
            'timer_warn': {
                'name': self._name,
                'time_left': time_left,
                'time_total': time_total,
                'epoch_minute': epoch_minute,
                'epoch_finish': epoch_finish,
            },
        }

        await self._executor.do_action(self._locations, action)

    async def _update(
            self, *,
            time_left: int, time_total: int,
            epoch_minute: float,
            epoch_finish: float):
        logger.info(
            "timer %s: time left %d, time total %s",
            self._name, time_left, time_total)

        action = {
            'timer_status': {
                'name': self._name,
                'time_left': time_left,
                'time_total': time_total,
                'epoch_minute': epoch_minute,
                'epoch_finish': epoch_finish,
            },
            'sound': {
                'name': "beep"
            },
        }

        if time_left % 5 == 0 and time_left > 0:
            action['message'] = {'text': '%d minutes' % time_left}

        await self._executor.do_action(self._locations, action)

    async def _sleep_until_time(self, new_time: float):
        twait = max(new_time - time.time(), 0)
        logger.debug(
            "timer %s: waiting %.1f seconds.",
            self._name, twait)
        await asyncio.sleep(twait)

    async def execute(self, total_minutes: int):

        if self._timer_running:
            await self._error("already set.")
            raise RuntimeError(
                "timer %s: already running, cannot execute" % self._name)

        try:
            self._timer_running = True

            early_warning = 2
            one_minute = 60

            current_time = time.time()
            timer_stop = current_time + total_minutes * one_minute

            logger.info(
                "timer %s: started at %d minutes.",
                self._name, total_minutes)
            await self._update(
                time_left=total_minutes,
                time_total=total_minutes,
                epoch_minute=current_time,
                epoch_finish=timer_stop)

            current_time = time.time()
            twait = timer_stop - current_time
            while twait > 0:
                logger.debug(
                    "timer %s: %.1f to go to.",
                    self._name, twait)

                # calculate absolute times
                seconds_to_next_minute = twait % one_minute
                if seconds_to_next_minute == 0:
                    seconds_to_next_minute = one_minute
                next_minute = current_time + seconds_to_next_minute
                next_warning = next_minute - early_warning

                # wait until early warning
                logger.debug(
                    "timer %s: waiting %.1f seconds to early warn, %.1f to go.",
                    self._name, next_warning - current_time, twait)
                await self._sleep_until_time(next_warning)

                # time: early_warning before minute
                current_time = time.time()
                minutes_left = int(
                    math.ceil(
                        (timer_stop - current_time - early_warning)
                        / one_minute
                    )
                )
                await self._warn(
                    time_left=minutes_left,
                    time_total=total_minutes,
                    epoch_minute=next_minute,
                    epoch_finish=timer_stop)

                # wait until minute
                current_time = time.time()
                twait = timer_stop - current_time
                logger.debug(
                    "timer %s: waiting %.1f seconds to minute, %.1f to go.",
                    self._name, next_minute - current_time, twait)
                await self._sleep_until_time(next_minute)

                # time: minute
                current_time = time.time()
                minutes_left = int(
                    math.ceil(
                        (timer_stop - current_time)
                        / one_minute
                    )
                )
                await self._update(
                    time_left=minutes_left,
                    time_total=total_minutes,
                    epoch_minute=next_minute,
                    epoch_finish=timer_stop)

                # calculate wait time
                current_time = time.time()
                twait = timer_stop - current_time

            logger.info(
                "timer %s: stopped after %d minutes.",
                self._name, total_minutes)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Timer encountered as error.")
            await self._error("crashed.")
        finally:
            self._timer_running = False


class Executor:
    def __init__(
            self, loop: asyncio.AbstractEventLoop, config: Dict) -> None:
        self._loop = loop
        self._config = config
        self._outputs = []  # type: List[Output]
        self._lock = asyncio.Lock()
        self._timers = {}  # type: Dict[str, Timer]
        self._schedule = None  # type: Optional['Schedule']

    def set_schedule(self, schedule: 'Schedule') -> None:
        self._schedule = schedule

    def add_output(self, output: Output) -> None:
        self._outputs.append(output)

    def action_required_for_locations(
            self, locations: Set[str], action: Action) -> Set[str]:

        # if timer action, we must process it everywhere.
        if 'timer' in action:
            return locations
        if 'template' in action:
            return locations

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

        if 'timer' in action:
            timer_details = action['timer']
            timer_name = timer_details['name']
            minutes = int(timer_details['minutes'])

            if (timer_name in self._timers and
                    self._timers[timer_name].is_running):
                logger.info(
                    "timer %s: Already running.", timer_name)
                raise RuntimeError(
                    "timer %s: already running" % timer_name)

            else:
                self._timers[timer_name] = Timer(
                    loop=self._loop,
                    executor=self,
                    locations=required_locations,
                    name=timer_name,
                )
                await self._timers[timer_name].execute(minutes)

        if 'template' in action and self._schedule is not None:
            template_details = action['template']
            template_name = template_details['name']
            await self._schedule.add_template(locations, template_name)

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
