"""FIX message parser."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fxfixparser.core.exceptions import ChecksumError, ParseError, ValidationError
from fxfixparser.core.field import FixField, FixFieldDefinition
from fxfixparser.core.message import FixMessage
from fxfixparser.spec.loader import load_spec_for_appl_ver_id
from fxfixparser.tags.dictionary import TagDictionary

if TYPE_CHECKING:
    from fxfixparser.venues.base import VenueHandler

logger = logging.getLogger(__name__)


@dataclass
class ParserConfig:
    """Configuration options for the FIX parser."""

    strict_checksum: bool = True
    strict_body_length: bool = False
    strict_delimiter: bool = False
    default_delimiter: str = "\x01"
    allow_pipe_delimiter: bool = True


class FixParser:
    """Parser for FIX protocol messages."""

    SOH = "\x01"
    PIPE = "|"

    # Cache of dictionaries layered with a FIX version spec, keyed by
    # (id(base_dictionary), appl_ver_id). Kept at class level so repeated
    # parses across parser instances share the merge cost.
    _spec_dict_cache: dict[tuple[int, str], TagDictionary] = {}

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
        auto_detect_venue: bool = False,
    ) -> FixMessage:
        """Parse a raw FIX message string into a FixMessage object.

        Args:
            raw_message: The raw FIX message string to parse.
            venue: Optional venue handler or venue name. When specified,
                   venue-specific tag definitions will be applied, which may
                   override generic definitions for the same tag numbers.
            auto_detect_venue: When True and no explicit ``venue`` is given,
                   the venue is detected from the message's component IDs and
                   its venue-specific tag definitions are applied. Has no
                   effect when ``venue`` is supplied.

        Returns:
            A FixMessage object containing the parsed fields.
        """
        if not raw_message or not raw_message.strip():
            raise ParseError("Empty message")

        # Resolve venue handler if needed
        venue_handler = self._resolve_venue(venue)

        normalized = self._normalize_delimiter(raw_message)
        raw_fields = self._extract_fields(normalized)

        if not raw_fields:
            raise ParseError("No valid fields found in message")

        # Layer the FIX version spec onto the base dictionary based on the
        # message's own ApplVerID (tag 1128). This means FIX 5.0 SP2 tags
        # like 1788, 2346, 1068 resolve without explicit configuration.
        spec_base = self._dictionary_for_message(raw_fields)

        # Layer venue tags + enum extensions on top
        dictionary = self._get_dictionary_for_venue(venue_handler, spec_base)

        fields = self._build_fields(raw_fields, dictionary)
        message = FixMessage(fields=fields, raw_message=raw_message)

        # Auto-detect the venue from the message's component IDs when no
        # explicit venue was given, then rebuild the fields against the
        # venue dictionary — otherwise venue custom tags stay Unknown.
        if venue_handler is None and auto_detect_venue:
            venue_handler = self._autodetect_venue(message)
            if venue_handler is not None:
                dictionary = self._get_dictionary_for_venue(venue_handler, spec_base)
                message = FixMessage(
                    fields=self._build_fields(raw_fields, dictionary),
                    raw_message=raw_message,
                )

        # Apply venue enrichment (also sets message.venue) when a handler
        # is specified or was auto-detected. This invokes any venue-
        # specific logic like SGX Titan OTC's product-name lookup.
        if venue_handler:
            message = venue_handler.enhance_message(message)

        self._validate_structure(message, normalized)

        return message

    def _autodetect_venue(self, message: FixMessage) -> VenueHandler | None:
        """Detect a venue handler from a parsed message's component IDs."""
        from fxfixparser.venues.registry import VenueRegistry

        return VenueRegistry.default().detect_from_message(message)

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
            if handler is None:
                logger.debug("No venue handler found for '%s'", venue)
            return handler

        return venue

    def _dictionary_for_message(self, raw_fields: list[tuple[int, str]]) -> TagDictionary:
        """Return a base dictionary with the message's FIX version spec layered on.

        Looks up tag 1128 (ApplVerID) in the raw fields and merges any bundled
        spec for that version into the parser's base dictionary. Fields already
        present in the base (e.g. FX-curated descriptions) are left untouched;
        the spec only fills in tags the base doesn't already define. Results
        are cached per (base dictionary, ApplVerID) so repeated parses pay the
        merge cost once.
        """
        appl_ver_id: str | None = None
        for tag, value in raw_fields:
            if tag == 1128:
                appl_ver_id = value
                break
        if not appl_ver_id:
            return self.dictionary

        cache_key = (id(self.dictionary), appl_ver_id)
        cached = self._spec_dict_cache.get(cache_key)
        if cached is not None:
            return cached

        spec_fields = load_spec_for_appl_ver_id(appl_ver_id)
        if not spec_fields:
            return self.dictionary

        merged = TagDictionary()
        for tag in self.dictionary.all_tags():
            defn = self.dictionary.get(tag)
            if defn:
                merged.add(defn)
        # For tags the base doesn't define, add the spec entry as-is.
        # For tags both define, keep the base's name/type/description
        # (curated for FX) but layer in any enum values the spec contributes
        # that the base lacks — so e.g. FIX 5.0 message types like "AI"
        # become decodable without losing the curated FIX 4.4 descriptions.
        for defn in spec_fields:
            existing = merged.get(defn.tag)
            if existing is None:
                merged.add(defn)
            elif defn.valid_values:
                # Spec values fill gaps; existing values win on conflicts.
                combined = {**defn.valid_values, **existing.valid_values}
                if combined != existing.valid_values:
                    merged.add(
                        FixFieldDefinition(
                            tag=existing.tag,
                            name=existing.name,
                            field_type=existing.field_type,
                            description=existing.description,
                            valid_values=combined,
                        )
                    )

        self._spec_dict_cache[cache_key] = merged
        logger.debug(
            "Layered FIX spec for ApplVerID=%s onto base dictionary " "(%d fields added).",
            appl_ver_id,
            len(merged.all_tags()) - len(self.dictionary.all_tags()),
        )
        return merged

    def _get_dictionary_for_venue(
        self,
        venue_handler: VenueHandler | None,
        base_dictionary: TagDictionary | None = None,
    ) -> TagDictionary:
        """Get a tag dictionary with venue-specific tags and enum extensions merged in."""
        base = base_dictionary if base_dictionary is not None else self.dictionary

        if venue_handler is None or (
            not venue_handler.custom_tags and not venue_handler.enum_extensions
        ):
            return base

        # Create a copy of the base dictionary and merge venue tags
        venue_dict = TagDictionary()
        for tag in base.all_tags():
            defn = base.get(tag)
            if defn:
                venue_dict.add(defn)
        # Then add/override with venue-specific tag definitions
        for defn in venue_handler.custom_tags:
            venue_dict.add(defn)
        # Finally, extend (not replace) enum values for standard tags
        for tag, extra_values in venue_handler.enum_extensions.items():
            existing = venue_dict.get(tag)
            if existing is not None:
                merged_values = {**existing.valid_values, **extra_values}
                venue_dict.add(
                    FixFieldDefinition(
                        tag=existing.tag,
                        name=existing.name,
                        field_type=existing.field_type,
                        description=existing.description,
                        valid_values=merged_values,
                    )
                )
            else:
                # No existing definition to extend — create a minimal one
                # so the venue's enum codes still decode.
                venue_dict.add(
                    FixFieldDefinition(
                        tag=tag,
                        name=f"Tag{tag}",
                        valid_values=dict(extra_values),
                    )
                )

        return venue_dict

    def _normalize_delimiter(self, message: str) -> str:
        """Normalize message delimiters and strip extraneous whitespace.

        FIX messages are single-line by definition. Newlines and carriage
        returns may appear when messages are copied from logs or files with
        line wrapping. These must be stripped so that tag=value pairs that
        were split across lines are reassembled correctly.

        When line breaks appear between fields (i.e. after a delimiter or
        before a new tag=value pair), they are replaced with SOH to preserve
        field boundaries.
        """
        # Replace line breaks that appear between fields (i.e. right
        # before a "tag=" pattern) with SOH to preserve field boundaries.
        message = re.sub(r"(\r\n|\r|\n)(?=\d+=)", self.SOH, message)
        # Strip remaining line breaks that are mid-value line wrapping
        # so that split values are reassembled correctly.
        message = message.replace("\r\n", "").replace("\r", "").replace("\n", "")
        if self.config.allow_pipe_delimiter and self.PIPE in message:
            return message.replace(self.PIPE, self.SOH)
        return message

    def _extract_fields(self, message: str) -> list[tuple[int, str]]:
        """Extract tag=value pairs from the message.

        In strict delimiter mode, SOH is required after each field.
        In non-strict mode (default), SOH is optional after the last field
        to be lenient with messages that omit the trailing delimiter.
        """
        if self.config.strict_delimiter:
            # Require SOH after every field (mandatory delimiter)
            pattern = r"(\d+)=([^" + self.SOH + r"]*)" + self.SOH
        else:
            # Allow optional trailing SOH (lenient for last field)
            pattern = r"(\d+)=([^" + self.SOH + r"]*)" + self.SOH + r"?"
        matches = re.findall(pattern, message)

        fields: list[tuple[int, str]] = []
        for tag_str, value in matches:
            try:
                tag = int(tag_str)
                fields.append((tag, value))
            except ValueError:
                logger.debug("Skipping field with non-numeric tag: '%s'", tag_str)
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

        # Validate declared body length if strict mode
        if self.config.strict_body_length:
            self._validate_body_length(message, normalized)

        # Validate checksum if strict mode
        if self.config.strict_checksum:
            self._validate_checksum(message, normalized)

    def _validate_body_length(self, message: FixMessage, normalized: str) -> None:
        """Validate the declared BodyLength (tag 9).

        Per the FIX specification, BodyLength is the number of characters in
        the message starting immediately after the SOH that terminates the
        BodyLength field, up to and including the SOH immediately preceding
        the CheckSum (tag 10) field.
        """
        begin_string_field = message.fields[0]  # tag 8 (validated above)
        body_length_field = message.fields[1]  # tag 9 (validated above)
        checksum_field = message.fields[-1]  # tag 10 (validated above)

        try:
            declared = int(body_length_field.raw_value)
        except ValueError:
            raise ValidationError(
                f"BodyLength (tag 9) is not numeric: " f"'{body_length_field.raw_value}'"
            )

        # The body begins immediately after the SOH terminating the
        # BodyLength field, i.e. after the "8=...<SOH>9=...<SOH>" prefix.
        prefix = (
            f"8={begin_string_field.raw_value}{self.SOH}"
            f"9={body_length_field.raw_value}{self.SOH}"
        )
        prefix_pos = normalized.find(prefix)
        if prefix_pos == -1:
            raise ValidationError("Cannot locate message body for BodyLength validation")
        body_start = prefix_pos + len(prefix)

        # The body ends at (and includes) the SOH immediately before "10=".
        search_pattern = self.SOH + "10=" + checksum_field.raw_value
        checksum_pos = normalized.rfind(search_pattern)
        if checksum_pos == -1:
            raise ValidationError("Cannot locate checksum for BodyLength validation")
        body_end = checksum_pos + 1  # include the SOH preceding "10="

        actual = body_end - body_start
        if actual != declared:
            raise ValidationError(f"BodyLength mismatch: declared {declared}, actual {actual}")

    def _validate_checksum(self, message: FixMessage, normalized: str) -> None:
        """Validate the message checksum.

        Uses the last tag-10 field from the parsed field list to correctly
        handle messages where "10=" may appear inside field values or as
        an earlier non-checksum tag.
        """
        checksum_field = message.fields[-1]
        if checksum_field.tag != 10:
            raise ValidationError("Missing CheckSum (tag 10)")

        # Build the checksum body: everything before the final "10=..." SOH.
        # Find the position by searching backwards for the SOH + "10="
        # pattern that corresponds to the last field.
        search_pattern = self.SOH + "10=" + checksum_field.raw_value
        checksum_pos = normalized.rfind(search_pattern)
        if checksum_pos != -1:
            # Include the SOH that precedes "10=" in the body
            body = normalized[: checksum_pos + 1]
        else:
            # Fallback: the message may start with "10=" (degenerate case)
            # or have no preceding SOH (e.g. "10=" is at position 0)
            prefix = "10=" + checksum_field.raw_value
            if normalized.endswith(prefix) or normalized.endswith(prefix + self.SOH):
                idx = normalized.rfind(prefix)
                body = normalized[:idx]
            else:
                raise ValidationError("Cannot locate checksum in message")

        expected = self.calculate_checksum(body)
        actual = checksum_field.raw_value

        if expected != actual:
            raise ChecksumError(expected, actual)

    @staticmethod
    def calculate_checksum(message: str) -> str:
        """Calculate the FIX checksum for a message body."""
        total = sum(ord(c) for c in message)
        return f"{total % 256:03d}"
