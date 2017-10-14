from typing import Callable
from logging import Logger


Func = Callable[..., None]
def simple_verbosity_option(logger: Logger) -> Callable[[Func], Func]: ...

def basic_config(logger: Logger) -> None: ...
