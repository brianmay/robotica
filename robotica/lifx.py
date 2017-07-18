import asyncio
import logging
from typing import List, Union, Optional

import yaml
from aiolifxc.aiolifx import Lights, Light, Color, DeviceOffline

logger = logging.getLogger(__name__)


class Lifx:
    def __init__(self, loop: asyncio.AbstractEventLoop, config: Union[None, str]) -> None:
        self._loop = loop
        if config is not None:
            with open(config, "r") as file:
                self._config = yaml.safe_load(file)
            self._disabled = self._config['disabled']
        else:
            self._disabled = True
        self._lights = Lights(loop=self._loop)

    def start(self) -> Optional[asyncio.Task]:
        if self._disabled:
            return None
        logger.debug("LIFX enabled.")
        return self._lights.start_discover()

    async def wake_up(self, labels: List[str], groups: List[str]) -> None:
        async def single_device(device: Light) -> None:
            try:
                power = await device.get_power()
                if not power:
                    await device.set_color(
                        Color(hue=0, saturation=0, brightness=0, kelvin=2500))
                await device.set_power(True)
                await device.set_color(
                    Color(hue=0, saturation=0, brightness=100, kelvin=2500),
                    duration=60000)
            except DeviceOffline:
                logger.error("Light is offline %s.", device)

        lights = self._lights.get_by_lists(
            groups=groups, labels=labels)  # type: Lights
        logger.info("Lifx wakeup for lights %s.", lights)
        await lights.do_for_every_device(Light, single_device)

    async def flash(self, labels: List[str], groups: List[str]) -> None:
        lights = self._lights.get_by_lists(
            groups=groups, labels=labels)  # type: Lights
        logger.info("Lifx flash for lights %s.", lights)
        await lights.set_waveform(
            color=Color(hue=0, saturation=100, brightness=100, kelvin=3500),
            transient=1,
            period=1000,
            cycles=2,
            duty_cycle=0,
            waveform=0,
        )

    def __str__(self) -> str:
        return ", ".join([str(b) for b in self._lights.light_list])
