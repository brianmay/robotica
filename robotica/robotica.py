"""Main module."""
import asyncio

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
        self._bulbs.turn_on_bedroom()
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
