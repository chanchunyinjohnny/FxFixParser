"""Venue registry for managing venue handlers."""

from fxfixparser.venues.base import VenueHandler
from fxfixparser.venues.bloomberg_dor import BloombergDORHandler
from fxfixparser.venues.fxgo import FXGOHandler
from fxfixparser.venues.smart_trade import SmartTradeHandler
from fxfixparser.venues.three_sixty_t import ThreeSixtyTHandler


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
        return registry
