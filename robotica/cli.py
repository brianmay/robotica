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
    scheduler.add_job(tasks.wake_up, 'cron', hour="06", minute="30", day_of_week="1-5")
    scheduler.add_job(tasks.wake_up_urgent, 'cron', hour="07", minute="00", day_of_week="1-5")
    scheduler.add_job(tasks.eat_breakfast, 'cron', hour="07", minute="10", day_of_week="1-5")
    scheduler.add_job(tasks.clean_teeth, 'cron', hour="07", minute="20", day_of_week="1-5")
    scheduler.add_job(tasks.get_into_car, 'cron', hour="07", minute="25", day_of_week="1-5")
    scheduler.add_job(tasks.go_to_bus, 'cron', hour="07", minute="30", day_of_week="1-5")
    scheduler.add_job(tasks.save_point, 'cron', hour="17", minute="55")
    scheduler.add_job(tasks.save_game, 'cron', hour="18", minute="00")
    scheduler.add_job(tasks.turn_off, 'cron', hour="18", minute="05")
    scheduler.add_job(tasks.pack_up, 'cron', hour="18", minute="10")
    scheduler.add_job(tasks.make_lunch, 'cron', hour="18", minute="20", day_of_week="0-4")
    scheduler.add_job(tasks.set_the_table, 'cron', hour="18", minute="25")
    scheduler.add_job(tasks.eat_tea, 'cron', hour="18", minute="30")
    scheduler.add_job(tasks.eat_dessert, 'cron', hour="19", minute="00")
    scheduler.add_job(tasks.shower, 'cron', hour="19", minute="15", day_of_week="0")
    scheduler.add_job(tasks.slow_down, 'cron', hour="19", minute="45")
    scheduler.add_job(tasks.read_in_bed, 'cron', hour="20", minute="00")
    scheduler.add_job(tasks.talk_in_bed, 'cron', hour="20", minute="15")
    scheduler.add_job(tasks.sleep, 'cron', hour="20", minute="30")

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
