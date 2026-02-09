"""FIX message parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fxfixparser.core.exceptions import ChecksumError, ParseError, ValidationError
from fxfixparser.core.field import FixField
from fxfixparser.core.message import FixMessage
from fxfixparser.tags.dictionary import TagDictionary

if TYPE_CHECKING:
    from fxfixparser.venues.base import VenueHandler


@dataclass
class ParserConfig:
    """Configuration options for the FIX parser."""

    strict_checksum: bool = True
    strict_body_length: bool = False
    default_delimiter: str = "\x01"
    allow_pipe_delimiter: bool = True


class FixParser:
    """Parser for FIX protocol messages."""

    SOH = "\x01"
    PIPE = "|"

    def __init__(
        self,
        config: ParserConfig | None = None,
        dictionary: TagDictionary | None = None,
    ) -> None:
        self.config = config or ParserConfig()
        self.dictionary = dictionary or TagDictionary.default()

    def parse(
        self,
        raw_message: str,
        venue: VenueHandler | str | None = None,
    ) -> FixMessage:
        """Parse a raw FIX message string into a FixMessage object.

        Args:
            raw_message: The raw FIX message string to parse.
            venue: Optional venue handler or venue name. When specified,
                   venue-specific tag definitions will be applied, which may
                   override generic definitions for the same tag numbers.

        Returns:
            A FixMessage object containing the parsed fields.
        """
        if not raw_message or not raw_message.strip():
            raise ParseError("Empty message")

        # Resolve venue handler if needed
        venue_handler = self._resolve_venue(venue)

        # Get dictionary with venue-specific tags merged in
        dictionary = self._get_dictionary_for_venue(venue_handler)

        normalized = self._normalize_delimiter(raw_message)
        raw_fields = self._extract_fields(normalized)

        if not raw_fields:
            raise ParseError("No valid fields found in message")

        fields = self._build_fields(raw_fields, dictionary)
        message = FixMessage(fields=fields, raw_message=raw_message)

        # Set venue on message if specified
        if venue_handler:
            message.venue = venue_handler.name

        self._validate_structure(message, normalized)

        return message

    def _resolve_venue(self, venue: VenueHandler | str | None) -> VenueHandler | None:
        """Resolve venue parameter to a VenueHandler instance."""
        if venue is None:
            return None

        if isinstance(venue, str):
            from fxfixparser.venues.registry import VenueRegistry
            registry = VenueRegistry.default()
            handler = registry.get(venue)
            if handler is None:
                # Try to match by sender ID
                handler = registry.get_by_sender_id(venue)
            return handler

        return venue

    def _get_dictionary_for_venue(
        self, venue_handler: VenueHandler | None
    ) -> TagDictionary:
        """Get a tag dictionary with venue-specific tags merged in."""
        if venue_handler is None or not venue_handler.custom_tags:
            return self.dictionary

        # Create a copy of the base dictionary and merge venue tags
        venue_dict = TagDictionary()
        # First add all base tags
        for tag in self.dictionary.all_tags():
            defn = self.dictionary.get(tag)
            if defn:
                venue_dict.add(defn)
        # Then add/override with venue-specific tags
        for defn in venue_handler.custom_tags:
            venue_dict.add(defn)

        return venue_dict

    def _normalize_delimiter(self, message: str) -> str:
        """Normalize message delimiters and strip extraneous whitespace.

        FIX messages are single-line by definition. Newlines and carriage
        returns may appear when messages are copied from logs or files with
        line wrapping. These must be stripped so that tag=value pairs that
        were split across lines are reassembled correctly.
        """
        # Strip newlines/carriage returns that break tag=value pairs
        message = message.replace("\r\n", "").replace("\r", "").replace("\n", "")
        if self.config.allow_pipe_delimiter and self.PIPE in message:
            return message.replace(self.PIPE, self.SOH)
        return message

    def _extract_fields(self, message: str) -> list[tuple[int, str]]:
        """Extract tag=value pairs from the message."""
        pattern = r"(\d+)=([^" + self.SOH + r"]*)" + self.SOH + r"?"
        matches = re.findall(pattern, message)

        fields: list[tuple[int, str]] = []
        for tag_str, value in matches:
            try:
                tag = int(tag_str)
                fields.append((tag, value))
            except ValueError:
                continue

        return fields

    def _build_fields(
        self, raw_fields: list[tuple[int, str]], dictionary: TagDictionary
    ) -> list[FixField]:
        """Build FixField objects with definitions from the dictionary."""
        fields: list[FixField] = []
        for tag, value in raw_fields:
            definition = dictionary.get(tag)
            fields.append(FixField(tag=tag, raw_value=value, definition=definition))
        return fields

    def _validate_structure(self, message: FixMessage, normalized: str) -> None:
        """Validate the FIX message structure."""
        if not message.fields:
            raise ValidationError("Message has no fields")

        # Check BeginString is first
        if message.fields[0].tag != 8:
            raise ValidationError("Message must start with BeginString (tag 8)")

        # Check BodyLength is second
        if len(message.fields) < 2 or message.fields[1].tag != 9:
            raise ValidationError("BodyLength (tag 9) must be second field")

        # Check MsgType is third
        if len(message.fields) < 3 or message.fields[2].tag != 35:
            raise ValidationError("MsgType (tag 35) must be third field")

        # Check CheckSum is last
        if message.fields[-1].tag != 10:
            raise ValidationError("Message must end with CheckSum (tag 10)")

        # Validate checksum if strict mode
        if self.config.strict_checksum:
            self._validate_checksum(message, normalized)

    def _validate_checksum(self, message: FixMessage, normalized: str) -> None:
        """Validate the message checksum."""
        checksum_field = message.get_field(10)
        if not checksum_field:
            raise ValidationError("Missing CheckSum (tag 10)")

        # Find position of checksum field
        checksum_start = normalized.rfind("10=")
        if checksum_start == -1:
            raise ValidationError("Cannot locate checksum in message")

        body = normalized[:checksum_start]
        expected = self.calculate_checksum(body)
        actual = checksum_field.raw_value

        if expected != actual:
            raise ChecksumError(expected, actual)

    @staticmethod
    def calculate_checksum(message: str) -> str:
        """Calculate the FIX checksum for a message body."""
        total = sum(ord(c) for c in message)
        return f"{total % 256:03d}"
