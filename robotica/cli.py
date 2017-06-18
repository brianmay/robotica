# -*- coding: utf-8 -*-

"""Console script for Robotica."""
import asyncio
import sys
from functools import partial

import aiolifx
import click
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from robotica.lifx import Bulbs
from robotica.robotica import Tasks


@click.command()
@click.option('--say_path', default="say", help='Path to say program.')
def main(say_path):
    """Console script for robotica."""
    bulbs = Bulbs()
    tasks = Tasks(bulbs, say_path)

    scheduler = AsyncIOScheduler()
    tasks.add_tasks_to_scheduler(scheduler)
    scheduler.start()

    loop = asyncio.get_event_loop()
    listener = loop.create_datagram_endpoint(
        partial(aiolifx.LifxDiscovery, loop, bulbs),
        local_addr=('0.0.0.0', aiolifx.aiolifx.UDP_BROADCAST_PORT))

    server = None
    try:
        server = loop.create_task(listener)
        loop.run_forever()
    finally:
        if server is not None:
            server.cancel()
        loop.remove_reader(sys.stdin)
        loop.close()


if __name__ == "__main__":
    main()
