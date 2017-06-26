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
@click.option('--say_path', default="say", help='Path to say program.')
@click.option('--schedule', default="schedule-sample.yaml", help='Path to schedule file.')
@click.option('--lifx/--no-lifx', default=False)
@click_log.simple_verbosity_option()
@click_log.init()
def main(say_path, schedule, lifx):
    """Console script for robotica."""
    loop = asyncio.get_event_loop()

    bulbs = Bulbs(loop)
    message = Audio(loop, say_path)
    schedule = Schedule(schedule, bulbs, message)

    scheduler = AsyncIOScheduler()
    scheduler.start()
    schedule.add_tasks_to_scheduler(scheduler)

    server = None

    if lifx:
        logger.debug("LIFX enabled.")
        listener = loop.create_datagram_endpoint(
            partial(aiolifxc.LifxDiscovery, loop, bulbs),
            local_addr=('0.0.0.0', aiolifxc.aiolifx.UDP_BROADCAST_PORT))
        server = loop.create_task(listener)
    else:
        logger.debug("LIFX disabled")

    try:
        loop.run_forever()
    finally:
        if server is not None:
            server.cancel()
        loop.close()


if __name__ == "__main__":
    main()
