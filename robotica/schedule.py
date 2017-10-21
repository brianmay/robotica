""" Robotica Schedule. """
import asyncio
import datetime
import math
import time
from typing import Dict, List, Set, Any, Optional, Tuple  # NOQA
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dateutil.parser import parse
import yaml
from apscheduler.schedulers.base import BaseScheduler

from robotica.executor import Executor, Action

logger = logging.getLogger(__name__)


_weekdays = {
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
    'sunday': 6,
}


class TimeEntry:
    def __init__(
            self,
            time: datetime.time,
            locations: Set[str],
            actions: List[Action]) -> None:
        self.time = time
        self.locations = locations
        self.actions = actions

    def to_json(self) -> Dict[str, Any]:
        return {
            'time': str(self.time),
            'locations': list(self.locations),
            'actions': self.actions,
        }

    def __str__(self) -> str:
        return "schedule@%s" % self.time

    def __repr__(self) -> str:
        return "<schedule %s %s %s>" % (
            self.time, self.locations, self.actions)


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
        self._timer_stop = None  # type: Optional[float]
        self._early_warning = 3
        self._one_minute = 60
        self._task = None  # type: Optional[asyncio.Task[None]]

    @property
    def is_running(self) -> bool:
        return self._task is not None

    def cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()

    async def _cancel(self, message: str):
        logger.info('timer %s: cancelled: %s', self._name, message)

        action = {
            'timer_cancel': {
                'name': self._name,
                'message': message,
            },
        }

        await self._executor.do_action(self._locations, action)

    async def _warn(
            self, *,
            time_left: int, time_total: int,
            epoch_minute: float,
            epoch_finish: float,
            action: Action):
        logger.info(
            "timer warn %s: time left %d, time total %s",
            self._name, time_left, time_total)

        new_action = {
            'timer_warn': {
                'name': self._name,
                'time_left': time_left,
                'time_total': time_total,
                'epoch_minute': epoch_minute,
                'epoch_finish': epoch_finish,
            },
        }
        new_action.update(action)

        await self._executor.do_action(self._locations, new_action)

    async def _update(
            self, *,
            time_left: int, time_total: int,
            epoch_minute: float,
            epoch_finish: float,
            action: Action):
        logger.info(
            "timer %s: time left %d, time total %s",
            self._name, time_left, time_total)

        new_action = {
            'timer_status': {
                'name': self._name,
                'time_left': time_left,
                'time_total': time_total,
                'epoch_minute': epoch_minute,
                'epoch_finish': epoch_finish,
            },
        }

        new_action.update(action)

        await self._executor.do_action(self._locations, new_action)

    async def _sleep_until_time(self, new_time: float):
        twait = max(new_time - time.time(), 0)
        logger.debug(
            "timer %s: waiting %.1f seconds.",
            self._name, twait)
        await asyncio.sleep(twait)

    def set_minutes(self, total_minutes: int) -> None:
        assert not self._timer_running
        current_time = time.time()
        self._timer_stop = current_time + total_minutes * self._one_minute

    def set_end_time(self, time_str: str) -> None:
        assert not self._timer_running
        hh, mm = time_str.split(":", maxsplit=1)
        hhmm = datetime.time(hour=int(hh), minute=int(mm))
        date = datetime.date.today()
        dt = datetime.datetime.combine(date=date, time=hhmm)
        self._timer_stop = dt.timestamp()

    async def _execute(self, action: Action) -> None:
        assert self._timer_stop is not None

        if self._timer_running:
            await self._cancel("already set.")
            raise RuntimeError(
                "timer %s: already running, cannot execute" % self._name)

        try:
            self._timer_running = True

            early_warning = self._early_warning
            one_minute = self._one_minute

            current_time = time.time()
            timer_stop = self._timer_stop
            next_minute = current_time
            total_minutes = int(
                math.ceil(
                    (timer_stop - current_time)
                    / one_minute
                )
            )

            logger.info(
                "timer %s: started at %d minutes.",
                self._name, total_minutes)

            while True:
                # calculate wait time
                current_time = time.time()
                twait = timer_stop - current_time

                logger.debug(
                    "timer %s: %.1f to go to.",
                    self._name, twait)

                if twait <= 0:
                    break

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
                    epoch_finish=timer_stop,
                    action=action)
                action = {}

                # calculate absolute times
                current_time = time.time()
                twait = timer_stop - current_time
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
                    epoch_finish=timer_stop,
                    action={})

                # wait until minute
                current_time = time.time()
                twait = timer_stop - current_time
                logger.debug(
                    "timer %s: waiting %.1f seconds to minute, %.1f to go.",
                    self._name, next_minute - current_time, twait)
                await self._sleep_until_time(next_minute)

            logger.info(
                "timer %s: stopped after %d minutes.",
                self._name, total_minutes)

        except asyncio.CancelledError:
            await self._cancel("Cancelled.")
            raise
        except Exception as e:
            logger.exception("Timer encountered as error.")
            await self._cancel("Crashed.")
        finally:
            self._timer_running = False
            self._task = None

    async def execute(self, action: Action) -> None:
        self._task = self._loop.create_task(self._execute(action))
        await self._task


class Scheduler:
    def __init__(
            self, *, loop: asyncio.AbstractEventLoop,
            config: str, executor: Executor) -> None:
        self._loop = loop
        self._schedule_path = config
        with open(config, "r") as file:
            self._schedule = yaml.safe_load(file)
        self._executor = executor
        self._scheduler = None  # type: Optional[BaseScheduler]
        self._timers = {}  # type: Dict[str, Timer]

    async def set_schedule(self, schedule: Dict):
        self._schedule = schedule
        assert self._scheduler is not None
        await self._prepare_for_day(self._scheduler)

    def save_schedule(self) -> None:
        with open(self._schedule_path, "w") as file:
            yaml.dump(self._schedule, stream=file)

    def start(self) -> None:
        scheduler = AsyncIOScheduler()
        scheduler.start()
        self._scheduler = scheduler
        self.add_tasks_to_scheduler()

    def stop(self) -> None:
        pass

    def _parse_entry(
            self, *,
            date: datetime.date,
            prev_time: Optional[datetime.time],
            locations: Set[str], entry: Dict,
            time_offset: Optional[datetime.time]) -> Tuple[List[TimeEntry], datetime.time]:
        result = []  # type: List[TimeEntry]

        locations = locations & set(entry.get('locations', locations))
        locations = locations - set(entry.get('locations_exclude', []))
        actions = list(entry.get('actions', []))

        time = entry['time']
        hours, minutes = map(int, time.split(':'))
        parsed_time = datetime.time(hour=hours, minute=minutes)

        if time_offset is not None:
            parsed_datetime = datetime.datetime.combine(date, parsed_time)
            delta = datetime.timedelta(
                hours=time_offset.hour, minutes=time_offset.minute)

            required_datetime = parsed_datetime + delta
            if required_datetime.date() != date:
                logger.error(
                    "Skipping time not for date: %s.",
                    required_datetime)

            parsed_time = required_datetime.time()

        if 'template' in entry:
            template_name = entry['template']
            template_result = self._expand_template(
                date=date,
                time=parsed_time,
                locations=locations,
                template_name=template_name,
            )
            result = result + template_result

        required_locations = set()  # type: Set[str]
        required_actions = []  # type: List[Action]
        for action in actions:
            locations_for_action = self._executor.action_required_for_locations(
                locations=locations,
                action=action
            )
            if len(locations_for_action) > 0:
                required_locations = required_locations | locations_for_action
                required_actions.append(action)

        if len(required_actions) > 0:
            result.append(TimeEntry(
                time=parsed_time,
                locations=required_locations,
                actions=required_actions,
            ))
            if 'timer' in entry:
                assert prev_time is not None
                timer = entry['timer'] or {}
                actions = [{
                    'timer': {
                        'name': timer.get('name', 'default'),
                        'end_time': parsed_time.strftime("%H:%M"),
                        'replace': True,
                    }
                }]
                result.append(TimeEntry(
                    time=prev_time,
                    locations=required_locations,
                    actions=actions,
                ))

        return result, parsed_time

    def _expand_template(
            self, date: datetime.date, time: datetime.time, locations: Set[str],
            template_name: str) -> List[TimeEntry]:
        result = []  # type: List[TimeEntry]

        template = self._schedule['template'][template_name]
        template_schedule = template['schedule']

        prev_time = None  # type: Optional[datetime.time]
        for template_entry in template_schedule:

            entry_result, prev_time = self._parse_entry(
                date=date,
                prev_time=prev_time,
                locations=locations,
                entry=template_entry,
                time_offset=time,
            )
            result = result + entry_result

        return result

    async def add_template(self, locations: Set[str], template_name: str) -> None:
        if template_name not in self._schedule['template']:
            return

        dt = datetime.datetime.now()
        date = dt.date()
        time = dt.time()
        hhmm = datetime.time(hour=time.hour, minute=time.minute)
        schedule = self._expand_template(date, time, locations, template_name)

        self._add_list_to_scheduler([
            task for task in schedule if task.time > hhmm
        ])

        for task in schedule:
            if task.time == hhmm:
                await self._do_task(task)

    def get_days_for_date(self, date: datetime.date) -> List[str]:
        results = []  # type: List[str]

        for name, day in self._schedule['day'].items():
            disabled = day.get('disabled', False)
            when = day.get('when')
            match = True

            if disabled:
                match = False
            elif when is not None:
                found_day_of_week = False
                if 'days_of_week' in when:
                    for required_day_of_week in when['days_of_week']:
                        required_value = _weekdays[required_day_of_week.lower()]
                        if date.weekday() == required_value:
                            found_day_of_week = True
                            break
                    if not found_day_of_week:
                        match = False
                if 'dates' in when:
                    found_date = False
                    for date_str in when['dates']:
                        if isinstance(date_str, str) and ' to ' in date_str:
                            split = date_str.split(" to ", maxsplit=1)
                            first_date = parse(split[0]).date()
                            last_date = parse(split[1]).date()
                        elif isinstance(date_str, str):
                            first_date = parse(date_str).date()
                            last_date = first_date
                        else:
                            first_date = date_str
                            last_date = date_str
                        if first_date <= date <= last_date:
                            found_date = True
                    if not found_date:
                        match = False

            if match:
                logger.debug("Adding schedule %s", name)
                results.append(name)

        # We can easily get from schedule -> replaces, but we want
        # to index the reverse relationship.
        replaced_by = {}  # type: Dict[str, List[str]]
        for name in results:
            replaced_by[name] = []
        for name in results:
            replaces_list = self._schedule['day'][name].get('replaces', [])
            for replaces in replaces_list:
                if replaces in replaced_by:
                    replaced_by[replaces].append(name)

        # For every leaf node - that is any node not in danger of being replaced,
        # we can process its replaces.
        n = 0
        while len(replaced_by) > 0 and n < 10:
            n += 1

            for name in list(replaced_by.keys()):

                # Skip entry if already been removed.
                if name not in replaced_by:
                    continue

                # Get the replaced_by list for the entry.
                replaced_by_list = replaced_by[name]

                # Skip node if not leaf node.
                # Node is a leaf node if no schedules are replacing it.
                if len(replaced_by_list) > 0:
                    continue

                # This node is a leaf, therefore it is not getting replaced.
                # As this node is staying, we should process its replaces list.
                replaces_list = self._schedule['day'][name].get('replaces', [])
                for replaces in replaces_list:
                    logger.debug("Replacing schedule %s", replaces)
                    # For every replaces, we should remove all references to this
                    # node.
                    for __, remove_list in replaced_by.items():
                        if replaces in remove_list:
                            remove_list.remove(replaces)
                    # Remove it from the dictionary.
                    if replaces in replaced_by:
                        del replaced_by[replaces]
                    # We also remove it from the results list.
                    if replaces in results:
                        results.remove(replaces)

                # Now we remove the leaf node from dictionary, so we
                # don't process it again.
                del replaced_by[name]

        # if too many loops, probably a loop in the replaces:
        if n >= 10:
            raise RuntimeError("Possible circular loop in replaces")

        return results

    def get_schedule_for_date(self, date: datetime.date) -> List[TimeEntry]:
        result = []  # type: List[TimeEntry]

        days = self.get_days_for_date(date)

        logger.info("Getting schedule for days %s.", days)
        for day in days:
            logger.debug("Adding day '%s' to schedule.", day)
            locations = set(self._schedule['day'][day]['locations'])
            schedule = self._schedule['day'][day]['schedule']

            prev_time = None  # type: Optional[datetime.time]
            for entry in schedule:
                entry_result, prev_time = self._parse_entry(
                    date=date,
                    prev_time=prev_time,
                    locations=locations,
                    entry=entry,
                    time_offset=None,
                )
                result = result + entry_result

        result = sorted(result, key=lambda e: e.time)
        return result

    async def do_actions(self, locations: Set[str], actions: List[Action]):
        if 'timer' in actions[0]:
            await self.set_timer(locations, actions)
        elif 'template' in actions[0]:
            await self.set_template(locations, actions)
        else:
            await self._executor.do_actions(locations, actions)

    async def _do_task(self, entry: TimeEntry) -> None:
        logger.info("%s: Waking up for %s.", datetime.datetime.now(), entry)
        await self.do_actions(entry.locations, entry.actions)

    async def _prepare_for_day(self, scheduler: BaseScheduler) -> None:
        logger.info("%s: Updating schedule.", datetime.datetime.now())
        self.add_tasks_to_scheduler()

    def _add_list_to_scheduler(self, schedule: List[TimeEntry]) -> None:
        if self._scheduler is None:
            return

        for entry in schedule:
            logger.debug("Adding entry '%s' to scheduler.", entry)
            hour = entry.time.hour
            minute = entry.time.minute

            scheduler = self._scheduler
            scheduler.add_job(
                self._do_task, 'cron', hour=hour, minute=minute,
                kwargs={'entry': entry}
            )

    def add_tasks_to_scheduler(self) -> None:
        if self._scheduler is None:
            return

        date = datetime.date.today()
        schedule = self.get_schedule_for_date(date)

        scheduler = self._scheduler
        scheduler.remove_all_jobs()
        scheduler.add_job(
            self._prepare_for_day, 'cron', hour="00", minute="00",
            kwargs={'scheduler': scheduler}
        )
        self._add_list_to_scheduler(schedule)

    async def set_timer(self, locations: Set[str], actions: List[Action]):
        assert 'timer' in actions[0]
        action = actions[0]

        timer_details = action['timer']
        timer_name = timer_details.get('name', 'default')
        timer_replace = timer_details.get('replace', False)
        timer_cancel = timer_details.get('cancel', False)

        timers = self._timers
        if timer_name in timers and timers[timer_name].is_running:
            if timer_replace or timer_cancel:
                logger.info(
                    "timer %s: Already running, cancelling old one.",
                    timer_name)
                timers[timer_name].cancel()
            else:
                logger.info(
                    "timer %s: Already running, not starting.",
                    timer_name)
                raise RuntimeError(
                    "timer %s: already running" % timer_name)

        # if request to cancel timer, don't start a new one
        if timer_cancel:
            return

        timer_action = dict(action)
        del timer_action['timer']

        timers[timer_name] = Timer(
            loop=self._loop,
            executor=self._executor,
            locations=locations,
            name=timer_name,
        )
        if 'minutes' in timer_details:
            minutes = int(timer_details['minutes'])
            timers[timer_name].set_minutes(minutes)
        elif 'end_time' in timer_details:
            end_time = timer_details['end_time']
            timers[timer_name].set_end_time(end_time)
        else:
            assert False
        await timers[timer_name].execute(timer_action)
        await self._executor.do_actions(locations, actions[1:])

    async def set_template(self, locations: Set[str], actions: List[Action]):
        assert 'template' in actions[0]
        template_details = actions[0]['template']
        template_name = template_details['name']
        await self.add_template(locations, template_name)
        await self._executor.do_actions(locations, actions[1:])
