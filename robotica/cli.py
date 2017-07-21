# -*- coding: utf-8 -*-

"""Console script for Robotica."""
import asyncio
import logging

import click
import click_log

from robotica.lifx import Lifx
from robotica.audio import Audio
from robotica.http import Http
from robotica.schedule import Schedule


logger = logging.getLogger(__name__)


@click.command()
@click.option('--audio', default="audio-sample.yaml", help='Path to audio.')
@click.option('--schedule', default="schedule-sample.yaml", help='Path to schedule config.')
@click.option('--lifx', default="lifx-sample.yaml", help='Path to LIFX config.')
@click.option('--http', default="http-sample.yaml", help='Path to HTTP config.')
@click_log.simple_verbosity_option()
@click_log.init()
def main(audio: str, schedule: str, lifx: str, http: str) -> None:
    """Console script for robotica."""
    loop = asyncio.get_event_loop()

    lifx_obj = Lifx(loop, lifx)
    lifx_obj.start()

    audio_obj = Audio(loop, audio)

    schedule_obj = Schedule(schedule, lifx_obj, audio_obj)
    schedule_obj.start()

    http_obj = Http(loop, http, schedule_obj)
    http_obj.start()

    try:
        loop.run_forever()
    finally:
        http_obj.stop()
        schedule_obj.stop()
        lifx_obj.stop()
        loop.close()


if __name__ == "__main__":
    main()
