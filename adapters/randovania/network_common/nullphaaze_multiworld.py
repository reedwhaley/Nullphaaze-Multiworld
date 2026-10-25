"""Private CDV session contract. GPL-3.0-or-later."""
from __future__ import annotations

from randovania.game.game_enum import RandovaniaGame

CONTRACT = "nullphaaze-multiworld-v1"
HEADER = "X-NullPhaaze-Multiworld"
BUILD_HEADER = "X-NullPhaaze-Build"
BUILD_ID = "nullphaaze-cdv-mw1-dev-20261025.1"
SUPPORTED_GAMES = (
    RandovaniaGame.METROID_PRIME,
    RandovaniaGame.METROID_PRIME_ECHOES,
    RandovaniaGame.METROID_PRIME_CORRUPTION,
)


def validate_contract(headers: dict[str, str]) -> None:
    if headers.get(HEADER) != CONTRACT:
        raise ValueError("Incompatible private CDV multiworld protocol; use the matching client/server package.")
    if headers.get(BUILD_HEADER) != BUILD_ID:
        raise ValueError("Mismatched private CDV build; install the client matching this server package.")
