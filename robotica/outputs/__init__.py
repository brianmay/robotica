from typing import Set

from robotica.types import Action


class Output:
    def is_action_required_for_locations(self, locations: Set[str], action: Action) -> bool:
        raise NotImplemented()

    async def execute(self, locations: Set[str], action: Action) -> None:
        raise NotImplemented()
