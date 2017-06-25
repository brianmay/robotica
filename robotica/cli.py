# -*- coding: utf-8 -*-

"""Console script for Robotica."""
import asyncio
import sys
from functools import partial
import logging

import aiolifx
import click
import click_log
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from robotica.lifx import Bulbs
from robotica.message import Message
from robotica.schedule import Schedule


logger = logging.getLogger(__name__)


@click.command()
@click.option('--say_path', default="say", help='Path to say program.')
@click.option('--schedule_path', default="sample.yaml", help='Path to schedule file.')
@click.option('--lifx/--no-lifx', default=False)
@click_log.simple_verbosity_option()
@click_log.init()
def main(say_path, schedule_path, lifx):
    """Console script for robotica."""
    loop = asyncio.get_event_loop()

    bulbs = Bulbs(loop)
    message = Message(loop, say_path)
    schedule = Schedule(schedule_path, bulbs, message)

    scheduler = AsyncIOScheduler()
    scheduler.start()
    schedule.add_tasks_to_scheduler(scheduler)

    server = None

    if lifx:
        logger.debug("LIFX enabled.")
        listener = loop.create_datagram_endpoint(
            partial(aiolifx.LifxDiscovery, loop, bulbs),
            local_addr=('0.0.0.0', aiolifx.aiolifx.UDP_BROADCAST_PORT))
        server = loop.create_task(listener)
    else:
        logger.debug("LIFX disabled")

    try:
        loop.run_forever()
    finally:
        if server is not None:
            server.cancel()
        loop.remove_reader(sys.stdin)
        loop.close()


if __name__ == "__main__":
    main()
