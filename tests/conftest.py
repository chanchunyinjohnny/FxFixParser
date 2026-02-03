"""Pytest configuration and shared fixtures."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.products.base import ProductRegistry
from fxfixparser.tags.dictionary import TagDictionary
from fxfixparser.venues.registry import VenueRegistry


@pytest.fixture
def parser() -> FixParser:
    """Create a parser with non-strict checksum validation."""
    config = ParserConfig(strict_checksum=False)
    return FixParser(config=config)


@pytest.fixture
def strict_parser() -> FixParser:
    """Create a parser with strict checksum validation."""
    config = ParserConfig(strict_checksum=True)
    return FixParser(config=config)


@pytest.fixture
def tag_dictionary() -> TagDictionary:
    """Create a default tag dictionary."""
    return TagDictionary.default()


@pytest.fixture
def venue_registry() -> VenueRegistry:
    """Create a default venue registry."""
    return VenueRegistry.default()


@pytest.fixture
def product_registry() -> ProductRegistry:
    """Create a default product registry."""
    return ProductRegistry.default()
