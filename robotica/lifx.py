import asyncio
import logging
from typing import List, Union, Set

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

    def start(self) -> None:
        if not self._disabled:
            logger.debug("LIFX enabled.")
            self._task = self._lights.start_discover()

    def stop(self) -> None:
        if not self._disabled:
            self._task.cancel()

    def _get_labels_for_locations(self, locations: Set[str]) -> Set[str]:
        labels = set()  # type: Set[str]
        if self._disabled:
            return set()
        for location in locations:
            labels = labels | set(self._config["location"].get(location, []))
        return labels

    def is_action_required_for_locations(self, locations: Set[str]) -> bool:
        labels = self._get_labels_for_locations(locations)
        return len(labels) > 0

    def _get_lights_from_locations(self, locations: Set[str]) -> Lights:
        labels = self._get_labels_for_locations(locations)
        lights = self._lights.get_by_lists(labels=list(labels))  # type: Lights
        return lights

    async def wake_up(self, locations: Set[str]) -> None:
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

        lights = self._get_lights_from_locations(locations)
        logger.info("Lifx wakeup for lights %s.", lights)
        await lights.do_for_every_device(Light, single_device)

    async def flash(self, locations: Set[str]) -> None:
        lights = self._get_lights_from_locations(locations)
        logger.info("Lifx flash for lights %s.", lights)
        await lights.set_waveform(
            color=Color(hue=0, saturation=100, brightness=100, kelvin=3500),
            transient=1,
            period=1000,
            cycles=2,
            duty_cycle=0,
            waveform=0,
        )
