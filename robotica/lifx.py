import asyncio

import aiolifx


class Bulbs:
    def __init__(self):
        self.bulbs = []  # type: List[aiolifx.aiolifx.Light]

    def register(self, bulb: aiolifx.aiolifx.Light) -> None:
        bulb.get_label()
        bulb.get_location()
        bulb.get_version()
        bulb.get_group()
        bulb.get_wififirmware()
        bulb.get_hostfirmware()
        self.bulbs.append(bulb)

    def unregister(self, bulb: aiolifx.aiolifx.Light) -> None:
        idx = 0
        for x in list([y.mac_addr for y in self.bulbs]):
            if x == bulb.mac_addr:
                del(self.bulbs[idx])
                break
            idx += 1

    async def turn_on_bedroom(self) -> None:
        bedroom_lights = filter(lambda b: b.group == 'Bedrooms', self.bulbs)
        for bulb in bedroom_lights:
            bulb.set_power(True)

    async def flash_bedroom(self) -> None:
        bedroom_lights = list(filter(lambda b: b.group == 'Bedrooms', self.bulbs))
        for i in range(5):
            for bulb in bedroom_lights:
                bulb.set_power(False)
            await asyncio.sleep(0.5)
            for bulb in bedroom_lights:
                bulb.set_power(True)
            await asyncio.sleep(0.5)
