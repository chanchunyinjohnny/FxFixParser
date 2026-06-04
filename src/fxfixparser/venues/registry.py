"""Venue registry for managing venue handlers."""

from fxfixparser.core.message import FixMessage
from fxfixparser.venues.base import VenueHandler
from fxfixparser.venues.bloomberg_dor import BloombergDORHandler
from fxfixparser.venues.fxgo import FXGOHandler
from fxfixparser.venues.lseg_fx_matching import LSEGFXMatchingHandler
from fxfixparser.venues.sgx_titan_otc import SGXTitanOTCHandler
from fxfixparser.venues.smart_trade import SmartTradeHandler
from fxfixparser.venues.three_sixty_t import ThreeSixtyTHandler

# FIX tags inspected, in priority order, when auto-detecting a venue from a
# parsed message: SenderCompID, TargetCompID, OnBehalfOfCompID. Checking the
# target/on-behalf tags lets client-to-venue messages (where the venue is the
# recipient, not the sender) resolve too.
_VENUE_ID_TAGS = (49, 56, 115)


class VenueRegistry:
    """Registry for venue handlers."""

    def __init__(self) -> None:
        self._venues: dict[str, VenueHandler] = {}

    def register(self, handler: VenueHandler) -> None:
        """Register a venue handler."""
        self._venues[handler.name.lower()] = handler

    def get(self, name: str) -> VenueHandler | None:
        """Get a venue handler by name."""
        return self._venues.get(name.lower())

    def get_by_sender_id(self, sender_comp_id: str | None) -> VenueHandler | None:
        """Get a venue handler by SenderCompID."""
        if not sender_comp_id:
            return None
        for handler in self._venues.values():
            if handler.matches_sender(sender_comp_id):
                return handler
        return None

    def detect_from_message(self, message: FixMessage) -> VenueHandler | None:
        """Detect a venue handler from a parsed message's component IDs.

        Checks SenderCompID (49), TargetCompID (56) and OnBehalfOfCompID
        (115) in that order, so client-to-venue messages — where the venue
        appears as the target rather than the sender — are detected too.
        """
        for tag in _VENUE_ID_TAGS:
            handler = self.get_by_sender_id(message.get_value(tag))
            if handler is not None:
                return handler
        return None

    def all_venues(self) -> list[VenueHandler]:
        """Get all registered venue handlers."""
        return list(self._venues.values())

    @classmethod
    def default(cls) -> "VenueRegistry":
        """Create a registry with default venue handlers."""
        registry = cls()
        registry.register(SmartTradeHandler())
        registry.register(FXGOHandler())
        registry.register(ThreeSixtyTHandler())
        registry.register(BloombergDORHandler())
        registry.register(SGXTitanOTCHandler())
        registry.register(LSEGFXMatchingHandler())
        return registry
