""" Robotica Schedule. """
import datetime
from typing import Dict
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

    def get_days_for_date(self, date: datetime.date):
        results = []
        for name, day in self._schedule['day'].items():
            when = day.get('when')
            match = True
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
            replaces = day.get('replaces', [])
            for replace in replaces:
                if replace in results:
                    results.remove(replace)
            if match:
                results.append(name)
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
        days = self.get_days_for_date(date)

        logger.info("Updating schedule for days %s.", days)
        scheduler.remove_all_jobs()
        scheduler.add_job(
            self.prepare_for_day, 'cron', hour="00", minute="00",
            kwargs={'scheduler': scheduler}
        )
        for day in days:
            logger.debug("Adding day '%s' to schedule.", day)
            schedule = self._schedule['day'][day]['schedule']
            for time, entry in schedule.items():
                logger.debug("Adding time '%s' to schedule with '%s'.", time, entry)
                hour, minute = time.split(':')
                scheduler.add_job(
                    self.do_task, 'cron', hour=hour, minute=minute,
                    kwargs={'entry': entry}
                )
