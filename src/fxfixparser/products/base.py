"""Abstract base class for product type handlers."""

from abc import ABC, abstractmethod
from typing import Any

from fxfixparser.core.message import FixMessage


class ProductHandler(ABC):
    """Abstract base class for FX product type handling."""

    @property
    @abstractmethod
    def product_type(self) -> str:
        """Return the product type name."""
        pass

    @abstractmethod
    def detect(self, message: FixMessage) -> bool:
        """Detect if the message is for this product type."""
        pass

    def extract_details(self, message: FixMessage) -> dict[str, Any]:
        """Extract product-specific details from the message."""
        return {"product_type": self.product_type}


class ProductRegistry:
    """Registry for product type handlers."""

    def __init__(self) -> None:
        self._handlers: list[ProductHandler] = []

    def register(self, handler: ProductHandler) -> None:
        """Register a product handler."""
        self._handlers.append(handler)

    def detect(self, message: FixMessage) -> ProductHandler | None:
        """Detect the product type for a message."""
        for handler in self._handlers:
            if handler.detect(message):
                return handler
        return None

    @classmethod
    def default(cls) -> "ProductRegistry":
        """Create a registry with default product handlers."""
        from fxfixparser.products.forward import ForwardHandler
        from fxfixparser.products.futures import FuturesHandler
        from fxfixparser.products.ndf import NDFHandler
        from fxfixparser.products.options import OptionsHandler
        from fxfixparser.products.spot import SpotHandler
        from fxfixparser.products.swap import SwapHandler

        registry = cls()
        # Order matters - more specific handlers first
        registry.register(SwapHandler())
        registry.register(NDFHandler())
        registry.register(OptionsHandler())
        registry.register(FuturesHandler())
        registry.register(ForwardHandler())
        registry.register(SpotHandler())  # Default/fallback
        return registry
