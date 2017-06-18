"""Main module."""
import asyncio

from apscheduler.schedulers.base import BaseScheduler

from robotica.lifx import Bulbs


class Tasks:
    def __init__(self, bulbs: Bulbs, say: str):
        self._bulbs = bulbs
        self._say = say

    async def say(self, text: str):
        process = await asyncio.create_subprocess_exec(self._say, text)
        await process.wait()

    async def wake_up(self) -> None:
        await self.say('Time to wake up.')
        await self._bulbs.turn_on_bedroom()

    async def wake_up_urgent(self) -> None:
        await self.say('Time to wake up RIGHT NOW.')
        await self._bulbs.flash_bedroom()

    async def eat_breakfast(self) -> None:
        await self.say('Time to eat breakfast.')

    async def clean_teeth(self) -> None:
        await self.say('It is time to clean your teeth.')

    async def get_into_car(self) -> None:
        await self.say('It is time to get into the Tesla and fasten your seat belts ready for take off.')

    async def go_to_bus(self) -> None:
        await self.say('It is time to take off for the school bus.')

    async def save_point(self) -> None:
        await self.say('It is time to go to your save point.')

    async def save_game(self) -> None:
        await self.say('It is time to save the gave.')

    async def turn_off(self) -> None:
        await self.say('It is time to turn off all electronic entertainment devices.')

    async def pack_up(self) -> None:
        await self.say('It is time to pack up.')

    async def make_lunch(self) -> None:
        await self.say('It is time to make lunch for tomorrow.')

    async def set_the_table(self) -> None:
        await self.say('It is time to set the table.')

    async def eat_tea(self) -> None:
        await self.say('It is time to eat tea.')

    async def eat_dessert(self) -> None:
        await self.say('It is time to eat dessert.')

    async def shower(self) -> None:
        await self.say('It is time to have a bath in the shower.')

    async def slow_down(self) -> None:
        await self.say('It is time to get tired for bed.')

    async def read_in_bed(self) -> None:
        await self.say('It is time to clean your teeth in bed and read.')

    async def talk_in_bed(self) -> None:
        await self.say('It is time to go to the toilet in bed and talk.')

    async def sleep(self) -> None:
        await self.say('It is time to go to the toilet and sleep.')

    def add_tasks_to_scheduler(self, scheduler: BaseScheduler):
        scheduler.add_job(self.wake_up, 'cron', hour="06", minute="30", day_of_week="0-4")
        scheduler.add_job(self.wake_up_urgent, 'cron', hour="07", minute="00", day_of_week="0-4")
        scheduler.add_job(self.eat_breakfast, 'cron', hour="07", minute="10", day_of_week="0-4")
        scheduler.add_job(self.clean_teeth, 'cron', hour="07", minute="20", day_of_week="0-4")
        scheduler.add_job(self.get_into_car, 'cron', hour="07", minute="25", day_of_week="0-4")
        scheduler.add_job(self.go_to_bus, 'cron', hour="07", minute="30", day_of_week="0-4")
        scheduler.add_job(self.save_point, 'cron', hour="17", minute="55")
        scheduler.add_job(self.save_game, 'cron', hour="18", minute="00")
        scheduler.add_job(self.turn_off, 'cron', hour="18", minute="05")
        scheduler.add_job(self.pack_up, 'cron', hour="18", minute="10")
        scheduler.add_job(self.make_lunch, 'cron', hour="18", minute="20", day_of_week="0-3,6")
        scheduler.add_job(self.set_the_table, 'cron', hour="18", minute="25")
        scheduler.add_job(self.eat_tea, 'cron', hour="18", minute="30")
        scheduler.add_job(self.eat_dessert, 'cron', hour="19", minute="00")
        scheduler.add_job(self.shower, 'cron', hour="19", minute="15", day_of_week="0")
        scheduler.add_job(self.slow_down, 'cron', hour="19", minute="45")
        scheduler.add_job(self.read_in_bed, 'cron', hour="20", minute="00")
        scheduler.add_job(self.talk_in_bed, 'cron', hour="20", minute="15")
        scheduler.add_job(self.sleep, 'cron', hour="20", minute="30")
