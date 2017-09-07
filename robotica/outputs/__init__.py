from typing import Set

from robotica.types import Action


class Output:
    def is_action_required_for_location(self, location: str, action: Action) -> bool:
        raise NotImplemented()

    async def execute(self, location: str, action: Action) -> None:
        raise NotImplemented()
