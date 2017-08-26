# -*- coding: utf-8 -*-

"""Console script for Robotica."""
import asyncio
import logging

import click
import click_log
from hbmqtt.client import MQTTClient

from robotica.executor import Executor
from robotica.inputs.http import HttpInput
from robotica.inputs.mqtt import MqttInput
from robotica.outputs.audio import AudioOutput
from robotica.outputs.lifx import LifxOutput
from robotica.outputs.mqtt import MqttOutput
from robotica.schedule import Schedule

logger = logging.getLogger('robotica')
click_log.basic_config(logger)


@click.command()
@click.option('--audio', default="config/audio.yaml", help='Path to audio config.')
@click.option('--lifx', default="config/lifx.yaml", help='Path to LIFX config.')
@click.option('--executor', default="config/executor.yaml", help='Path to executor config.')
@click.option('--schedule', default="config/schedule.yaml", help='Path to schedule config.')
@click.option('--http', default="config/http.yaml", help='Path to HTTP config.')
@click.option('--mqtt', default="config/mqtt.yaml", help='Path to MQTT config.')
@click_log.simple_verbosity_option(logger)
def main(
        audio: str, lifx: str, executor: str,
        schedule: str, http: str, mqtt: str) -> None:
    """Console script for robotica."""
    loop = asyncio.get_event_loop()
    client = MQTTClient()

    lifx_output = LifxOutput(loop, lifx)
    lifx_output.start()

    audio_output = AudioOutput(loop, audio)

    mqtt_output = MqttOutput(loop, audio, client)

    executor_obj = Executor(loop, executor)
    executor_obj.add_output(audio_output)
    executor_obj.add_output(lifx_output)
    executor_obj.add_output(mqtt_output)

    schedule_obj = Schedule(schedule, executor_obj)
    schedule_obj.start()

    http_input = HttpInput(loop, http, executor_obj, schedule_obj)
    http_input.start()

    mqtt_input = MqttInput(loop, mqtt, executor_obj, schedule_obj, client)
    mqtt_input.start()

    try:
        loop.run_forever()
    finally:
        mqtt_input.stop()
        http_input.stop()
        schedule_obj.stop()
        lifx_output.stop()
        pending = asyncio.Task.all_tasks()
        for p in pending:
            p.cancel()
            try:
                loop.run_until_complete(p)
            except asyncio.CancelledError:
                pass
        loop.close()
