# -*- coding: utf-8 -*-

"""Console script for Robotica."""
import asyncio
import importlib
import logging
from typing import List, Any  # NOQA

import click
import click_log
import yaml

from robotica.executor import Executor
from robotica.plugins import Plugin  # NOQA
from robotica.plugins.inputs import Input
from robotica.plugins.outputs import Output
from robotica.schedule import Scheduler

logger = logging.getLogger('robotica')
click_log.basic_config(logger)


def _load_class(class_name: str) -> Any:
    """
    Dynamically load a class from a string
    """

    class_data = class_name.split(".")
    module_path = ".".join(class_data[:-1])
    class_str = class_data[-1]

    class_module = importlib.import_module(module_path)
    return getattr(class_module, class_str)


@click.command()
@click.option('--config', default="config/config.yaml", help='Path to config.')
@click.option('--schedule', default="config/schedule.yaml", help='Path to schedule config or None.')
@click_log.simple_verbosity_option(logger)
def main(config: str, schedule: str) -> None:
    """Console script for robotica."""
    with open(config, "r") as file:
        config_dict = yaml.safe_load(file)
        output_dict = config_dict['outputs']
        input_dict = config_dict['inputs']

    loop = asyncio.get_event_loop()
    plugins = []  # type: List[Plugin]

    executor_obj = Executor(loop, config_dict['executor'])
    executor_obj.start()
    for name in output_dict.keys():
        output_plugin_config = output_dict[name]
        output_plugin_class = _load_class(output_plugin_config['plugin'])
        assert issubclass(output_plugin_class, Output)
        output_plugin = output_plugin_class(
            name=name,
            loop=loop,
            config=output_plugin_config,
        )
        output_plugin.start()
        executor_obj.add_output(output_plugin)
        plugins.append(output_plugin)

    if schedule.upper() == "NONE":
        scheduler_obj = None
    else:
        scheduler_obj = Scheduler(
            loop=loop,
            config=schedule,
            executor=executor_obj,
        )
        scheduler_obj.start()
        executor_obj.set_scheduler(scheduler_obj)

    for name in input_dict.keys():
        input_plugin_config = input_dict[name]

        input_plugin_class = _load_class(input_plugin_config['plugin'])
        assert issubclass(input_plugin_class, Input)
        input_plugin = input_plugin_class(
            name=name,
            loop=loop,
            config=input_plugin_config,
            executor=executor_obj,
            scheduler=scheduler_obj,
        )
        input_plugin.start()
        plugins.append(input_plugin)

    try:
        loop.run_forever()
    finally:
        executor_obj.stop()
        for plugin in reversed(plugins):
            plugin.stop()
        pending = asyncio.Task.all_tasks()
        for p in pending:
            p.cancel()
            try:
                loop.run_until_complete(p)
            except asyncio.CancelledError:
                pass
        loop.close()
