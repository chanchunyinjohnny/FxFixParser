"""360T venue handler."""

from fxfixparser.venues.base import VenueHandler


class ThreeSixtyTHandler(VenueHandler):
    """Handler for 360T FIX messages."""

    @property
    def name(self) -> str:
        return "360T"

    @property
    def sender_comp_ids(self) -> list[str]:
        return ["360T", "THREESIXTYT", "360TGTX"]
