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
            bulb.set_color([58275, 0, 65365, 2500], duration=60000)

    async def flash_bedroom(self) -> None:
        bedroom_lights = list(filter(lambda b: b.group == 'Bedrooms', self.bulbs))
        for bulb in bedroom_lights:
            # transient, color, period,cycles,duty_cycle,waveform
            bulb.set_waveform({
                "color": [0, 0, 0, 3500],
                "transient": 1,
                "period": 100,
                "cycles": 30,
                "duty_cycle": 0,
                "waveform": 0
            })
