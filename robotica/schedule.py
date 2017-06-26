""" Robotica Schedule. """
import datetime
from typing import Dict, List
import logging

import yaml
from apscheduler.schedulers.base import BaseScheduler

from robotica.lifx import Bulbs
from robotica.message import Message

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
    def __init__(self, schedule_path: str, bulbs: Bulbs, message: Message):
        with open(schedule_path, "r") as file:
            self._schedule = yaml.safe_load(file)
        self._bulbs = bulbs
        self._message = message

    def get_days_for_date(self, date: datetime.date) -> List[str]:
        results = []  # type: List[str]
        remove = set()  # type: Set[str]

        for name, day in self._schedule['day'].items():
            disabled = day.get('disabled', False)
            if disabled:
                when = None
                match = False
            else:
                match = True
                when = day.get('when')
            if when is not None:
                match = False
                if 'days_of_week' in when:
                    for required_day_of_week in when['days_of_week']:
                        required_value = _weekdays[required_day_of_week.lower()]
                        if date.weekday() == required_value:
                            match = True
                            break
                else:
                    logger.error("Error processing when name %s entry %s", name, day)
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
