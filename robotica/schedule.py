""" Robotica Schedule. """
import datetime
from typing import Dict, List, Set
import logging

from dateutil.parser import parse
import yaml
from apscheduler.schedulers.base import BaseScheduler

from robotica.lifx import Bulbs
from robotica.audio import Audio

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


class Schedule:
    def __init__(self, schedule_path: str, bulbs: Bulbs, message: Audio):
        with open(schedule_path, "r") as file:
            self._schedule = yaml.safe_load(file)
        self._expand_templates()
        self._bulbs = bulbs
        self._message = message

    def _expand_templates(self):
        today = datetime.date.today()
        for name, day in self._schedule['day'].items():
            schedule = day['schedule']
            new_schedule = []
            for entry in schedule:

                if 'template' in entry:
                    time = entry['time']
                    hours, minutes = map(int, time.split(':'))
                    source_time = datetime.time(hour=hours, minute=minutes)
                    source_datetime = datetime.datetime.combine(today, source_time)

                    template_name = entry['template']
                    template = self._schedule['template'][template_name]
                    template_schedule = template['schedule']

                    for template_entry in template_schedule:
                        delta_time = template_entry['time']
                        delta_hours, delta_minutes = map(int, delta_time.split(':'))
                        delta = datetime.timedelta(hours=delta_hours, minutes=delta_minutes)

                        required_datetime = source_datetime + delta
                        if required_datetime.date() != today:
                            logger.error(
                                "Skipping template as time not for today: %s.",
                                required_datetime)
                            continue

                        str_time = required_datetime.strftime('%H:%M')
                        new_entry = dict(template_entry)
                        new_entry['time'] = str_time
                        self._schedule['day'][name]['schedule'].append(new_entry)
                else:
                    new_schedule.append(entry)
            day['schedule'] = new_schedule

    def get_days_for_date(self, date: datetime.date) -> List[str]:
        results = []  # type: List[str]
        remove = set()  # type: Set[str]

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
                replaces = day.get('replaces', [])
                remove.update(replaces)
                logger.debug("Adding day %s to schedule.", name)
                results.append(name)

        for name in remove:
            if name in results:
                logger.debug("Removing day %s from schedule.", name)
                results.remove(name)

        return results

    def get_schedule_for_date(self, date: datetime.date) -> List[Dict[str, str]]:
        days = self.get_days_for_date(date)

        logger.info("Getting schedule for days %s.", days)
        results = []  # type: List[Dict[str,str]]
        for day in days:
            logger.debug("Adding day '%s' to schedule.", day)
            schedule = self._schedule['day'][day]['schedule']
            for entry in schedule:
                logger.debug("Adding entry '%s' to schedule", entry)
                results.append(entry)
        return results

    async def do_task(self, entry: Dict[str, Dict[str, str]]):
        logger.info("%s: Waking up for %s.", datetime.datetime.now(), entry)

        if 'lights' in entry:
            action = entry['lights']['action']
            if 'group' in entry['lights']:
                group = entry['lights']['group']
                bulbs = self._bulbs.get_by_group(group)
            elif 'label' in entry['lights']:
                label = entry['lights']['label']
                bulbs = self._bulbs.get_by_label(label)
            else:
                groups = entry['lights'].get('groups', [])
                labels = entry['lights'].get('labels', [])
                bulbs = self._bulbs.get_by_lists(groups=groups, labels=labels)

            logger.debug("About to '%s' lights %s", action, bulbs)
            await getattr(bulbs, action)()

        if 'message' in entry:
            logger.debug("About to say '%s'.", entry['message']['text'])
            await self._message.say(entry['message']['text'])

    async def prepare_for_day(self, scheduler: BaseScheduler):
        logger.info("%s: Updating schedule.", datetime.datetime.now())
        self.add_tasks_to_scheduler(scheduler)

    def add_tasks_to_scheduler(self, scheduler: BaseScheduler):
        date = datetime.date.today()
        schedule = self.get_schedule_for_date(date)

        scheduler.remove_all_jobs()
        scheduler.add_job(
            self.prepare_for_day, 'cron', hour="00", minute="00",
            kwargs={'scheduler': scheduler}
        )
        for entry in schedule:
            logger.debug("Adding entry '%s' to scheduler.", entry)
            hour, minute = entry['time'].split(':')
            scheduler.add_job(
                self.do_task, 'cron', hour=hour, minute=minute,
                kwargs={'entry': entry}
            )
