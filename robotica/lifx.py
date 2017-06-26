import asyncio
import logging
from functools import partial
from typing import List, Coroutine, Callable, Union

import aiolifxc
import yaml
from aiolifxc.aiolifx import DeviceOffline

logger = logging.getLogger(__name__)


class Bulbs:
    def __init__(self, loop: asyncio.AbstractEventLoop, config: str):
        self._loop = loop
        with open(config, "r") as file:
            self._config = yaml.safe_load(file)
        self._disabled = self._config['disabled']
        self.bulbs = []  # type: List[aiolifxc.aiolifx.Light]

    def start(self) -> Union[asyncio.Task, None]:
        if self._disabled:
            return None
        logger.debug("LIFX enabled.")
        listener = self._loop.create_datagram_endpoint(
            partial(aiolifxc.LifxDiscovery, self._loop, self),
            local_addr=('0.0.0.0', aiolifxc.aiolifx.UDP_BROADCAST_PORT))
        return self._loop.create_task(listener)

    def register(self, bulb: aiolifxc.aiolifx.Light) -> None:
        logger.info("Register light %s.", bulb.mac_addr)
        self._loop.create_task(self.async_register(bulb))

    async def async_register(self, bulb: aiolifxc.aiolifx.Light) -> None:
        try:
            await bulb.get_metadata(loop=self._loop)
            self.bulbs.append(bulb)
            logger.info("Got light %s (%s).", bulb.mac_addr, bulb.label)
        except DeviceOffline:
            logger.error("Light is offline %s", bulb.mac_addr)

    def unregister(self, bulb: aiolifxc.aiolifx.Light) -> None:
        logger.info("Unregister light %s (%s).", bulb.mac_addr, bulb.label)
        idx = 0
        for x in list([y.mac_addr for y in self.bulbs]):
            if x == bulb.mac_addr:
                del(self.bulbs[idx])
                break
            idx += 1

    def get_by_group(self, group: str) -> 'Bulbs':
        result = Bulbs(self._loop)
        result.bulbs = list(filter(lambda b: b.group == group, self.bulbs))
        return result

    def get_by_label(self, label: str) -> 'Bulbs':
        result = Bulbs(self._loop)
        result.bulbs = list(filter(lambda b: b.label == label, self.bulbs))
        return result

    def get_by_lists(self, *, groups: List[str]=None, labels: List[str]=None) -> 'Bulbs':
        lights = set()
        if groups is not None:
            for group in groups:
                lights |= set(filter(lambda b: b.group == group, self.bulbs))
        if labels is not None:
            for label in labels:
                lights |= set(filter(lambda b: b.label == label, self.bulbs))
        result = Bulbs(self._loop)
        result.bulbs = list(lights)
        return result

    async def _do_for_every_light(self, fun: Callable[[aiolifxc.aiolifx.Light], Coroutine[any, any, None]]):
        coroutines = []
        for bulb in self.bulbs:
            try:
                coroutines.append(fun(bulb))
            except DeviceOffline:
                logger.info("Light is offline %s (%s).", bulb.mac_addr, bulb.label)
        await asyncio.gather(*coroutines, loop=self._loop)

    @staticmethod
    async def _wake_up(bulb: aiolifxc.aiolifx.Light) -> None:
        power = await bulb.get_power()
        if not power:
            await bulb.set_color([58275, 0, 0, 2500])
        await bulb.set_power(True)
        await bulb.set_color([58275, 0, 65365, 2500], duration=60000)

    async def wake_up(self) -> None:
        await self._do_for_every_light(self._wake_up)

    @staticmethod
    async def _flash(bulb: aiolifxc.aiolifx.Light) -> None:
        # transient, color, period,cycles,duty_cycle,waveform
        await bulb.set_waveform({
            "color": [0, 0, 0, 3500],
            "transient": 1,
            "period": 100,
            "cycles": 30,
            "duty_cycle": 0,
            "waveform": 0
        })

    async def flash(self) -> None:
        await self._do_for_every_light(self._flash)

    def __str__(self):
        return ", ".join([str(b.label) for b in self.bulbs])
