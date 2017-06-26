# -*- coding: utf-8 -*-

"""Console script for Robotica."""
import asyncio
from functools import partial
import logging

import aiolifxc
import click
import click_log
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from robotica.lifx import Bulbs
from robotica.audio import Audio
from robotica.schedule import Schedule


logger = logging.getLogger(__name__)


@click.command()
@click.option('--audio', default="audio-sample.yaml", help='Path to audio.')
@click.option('--schedule', default="schedule-sample.yaml", help='Path to schedule config.')
@click.option('--lifx', default="lifx-sample.yaml", help='Path to LIFX config.')
@click_log.simple_verbosity_option()
@click_log.init()
def main(audio, schedule, lifx):
    """Console script for robotica."""
    loop = asyncio.get_event_loop()

    bulbs = Bulbs(loop, lifx)
    server = bulbs.start()

    message = Audio(loop, audio)
    schedule = Schedule(schedule, bulbs, message)

    scheduler = AsyncIOScheduler()
    scheduler.start()
    schedule.add_tasks_to_scheduler(scheduler)

    try:
        loop.run_forever()
    finally:
        if server is not None:
            server.cancel()
        loop.close()


if __name__ == "__main__":
    main()
