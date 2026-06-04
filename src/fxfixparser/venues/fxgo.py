"""Bloomberg FXGO venue handler."""

from fxfixparser.venues.base import VenueHandler


class FXGOHandler(VenueHandler):
    """Handler for Bloomberg FXGO FIX messages."""

    @property
    def name(self) -> str:
        return "Bloomberg FXGO"

    @property
    def sender_comp_ids(self) -> list[str]:
        return ["FXGO", "BLOOMBERG", "BBG", "BFXGO"]
