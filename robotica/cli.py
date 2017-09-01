# -*- coding: utf-8 -*-

"""Console script for Robotica."""
import asyncio
import logging
import yaml

import click
import click_log

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
@click.option('--config', default="config/config.yaml", help='Path to config.')
@click.option('--schedule', default="config/schedule.yaml", help='Path to schedule config.')
@click_log.simple_verbosity_option(logger)
def main(config: str, schedule: str) -> None:
    """Console script for robotica."""
    with open(config, "r") as file:
        config_dict = yaml.safe_load(file)
        output_dict = config_dict['outputs']
        input_dict = config_dict['inputs']

    loop = asyncio.get_event_loop()

    lifx_output = LifxOutput(loop, output_dict['lifx'])
    lifx_output.start()

    audio_output = AudioOutput(loop, output_dict['audio'])
    audio_output.start()

    mqtt_output = MqttOutput(loop, output_dict['mqtt'])
    mqtt_output.start()

    executor_obj = Executor(loop, config_dict['executor'])
    executor_obj.add_output(audio_output)
    executor_obj.add_output(lifx_output)
    executor_obj.add_output(mqtt_output)

    schedule_obj = Schedule(schedule, executor_obj)
    schedule_obj.start()

    http_input = HttpInput(loop, input_dict['http'], executor_obj, schedule_obj)
    http_input.start()

    mqtt_input = MqttInput(loop, input_dict['mqtt'], executor_obj, schedule_obj)
    mqtt_input.start()

    try:
        loop.run_forever()
    finally:
        mqtt_input.stop()
        http_input.stop()
        schedule_obj.stop()
        mqtt_output.stop()
        audio_output.stop()
        lifx_output.stop()
        pending = asyncio.Task.all_tasks()
        for p in pending:
            p.cancel()
            try:
                loop.run_until_complete(p)
            except asyncio.CancelledError:
                pass
        loop.close()
