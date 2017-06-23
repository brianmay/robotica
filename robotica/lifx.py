import asyncio
from typing import List

import aiolifx


class Bulbs:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self.bulbs = []  # type: List[aiolifx.aiolifx.Light]

    def register(self, bulb: aiolifx.aiolifx.Light) -> None:
        print("register", bulb.mac_addr, bulb)
        self._loop.create_task(bulb.get_metadata(loop=self._loop))
        self.bulbs.append(bulb)

    def unregister(self, bulb: aiolifx.aiolifx.Light) -> None:
        print("unregister", bulb.mac_addr, bulb)
        idx = 0
        for x in list([y.mac_addr for y in self.bulbs]):
            if x == bulb.mac_addr:
                del(self.bulbs[idx])
                break
            idx += 1

    async def turn_on_bedroom(self) -> None:
        bedroom_lights = filter(lambda b: b.group == 'Bedrooms', self.bulbs)
        for bulb in bedroom_lights:
            power = await bulb.get_power()
            if not power:
                await bulb.set_color([58275, 0, 0, 2500])
            await bulb.set_power(True)
            await bulb.set_color([58275, 0, 65365, 2500], duration=60000)

    async def flash_bedroom(self) -> None:
        bedroom_lights = list(filter(lambda b: b.group == 'Bedrooms', self.bulbs))
        for bulb in bedroom_lights:
            # transient, color, period,cycles,duty_cycle,waveform
            await bulb.set_waveform({
                "color": [0, 0, 0, 3500],
                "transient": 1,
                "period": 100,
                "cycles": 30,
                "duty_cycle": 0,
                "waveform": 0
            })
