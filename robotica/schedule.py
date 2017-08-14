""" Robotica Schedule. """
import datetime
from typing import Dict, List, Set, Any, Optional  # NOQA
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


class Schedule:
    def __init__(self, schedule_path: str, executor: Executor) -> None:
        with open(schedule_path, "r") as file:
            self._schedule = yaml.safe_load(file)
        self._executor = executor

    def start(self) -> None:
        scheduler = AsyncIOScheduler()
        scheduler.start()
        self.add_tasks_to_scheduler(scheduler)

    def stop(self) -> None:
        pass

    def _parse_entry(
            self,
            date: datetime.date,
            locations: Set[str], entry: Dict,
            time_offset: Optional[datetime.time]) -> List[TimeEntry]:
        result = []  # type: List[TimeEntry]

        locations = locations | set(entry.get('locations', []))
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

        actions = [
            action
            for action in actions
            if self._executor.is_action_required_for_locations(
                locations, action)
        ]

        if len(actions) > 0:
            result.append(TimeEntry(
                time=parsed_time,
                locations=locations,
                actions=actions,
            ))

        return result

    def _expand_template(
            self, date: datetime.date, time: datetime.time, locations: Set[str],
            template_name: str) -> List[TimeEntry]:
        result = []  # type: List[TimeEntry]

        template = self._schedule['template'][template_name]
        template_schedule = template['schedule']

        for template_entry in template_schedule:

            entry_result = self._parse_entry(
                date=date,
                locations=locations,
                entry=template_entry,
                time_offset=time,
            )
            result = result + entry_result

        return result

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

            for entry in schedule:
                entry_result = self._parse_entry(
                    date=date,
                    locations=locations,
                    entry=entry,
                    time_offset=None,
                )
                result = result + entry_result

        result = sorted(result, key=lambda e: e.time)
        return result

    async def do_task(self, entry: TimeEntry) -> None:
        logger.info("%s: Waking up for %s.", datetime.datetime.now(), entry)
        await self._executor.do_actions(entry.locations, entry.actions)

    async def prepare_for_day(self, scheduler: BaseScheduler) -> None:
        logger.info("%s: Updating schedule.", datetime.datetime.now())
        self.add_tasks_to_scheduler(scheduler)

    def add_tasks_to_scheduler(self, scheduler: BaseScheduler) -> None:
        date = datetime.date.today()
        schedule = self.get_schedule_for_date(date)

        scheduler.remove_all_jobs()
        scheduler.add_job(
            self.prepare_for_day, 'cron', hour="00", minute="00",
            kwargs={'scheduler': scheduler}
        )
        for entry in schedule:
            logger.debug("Adding entry '%s' to scheduler.", entry)
            hour = entry.time.hour
            minute = entry.time.minute
            scheduler.add_job(
                self.do_task, 'cron', hour=hour, minute=minute,
                kwargs={'entry': entry}
            )
