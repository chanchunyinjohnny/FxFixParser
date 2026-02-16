"""FIX field data models."""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FixFieldDefinition:
    """Definition of a FIX field from the data dictionary."""

    tag: int
    name: str
    field_type: str = "STRING"
    description: str = ""
    valid_values: dict[str, str] = field(default_factory=dict)

    def get_value_description(self, value: str) -> str | None:
        """Get the description for an enumerated value."""
        return self.valid_values.get(value)


@dataclass
class FixField:
    """A parsed FIX field with its value and definition."""

    tag: int
    raw_value: str
    definition: FixFieldDefinition | None = None

    @property
    def name(self) -> str:
        """Get the field name from the definition, or 'Unknown' if not defined."""
        if self.definition:
            return self.definition.name
        return f"Unknown({self.tag})"

    @property
    def description(self) -> str:
        """Get the field description from the definition."""
        if self.definition:
            return self.definition.description
        return ""

    @property
    def value_description(self) -> str | None:
        """Get the description for the current value if it's an enumerated type."""
        if self.definition:
            return self.definition.get_value_description(self.raw_value)
        return None

    @property
    def typed_value(self) -> Any:
        """Convert the raw value to the appropriate Python type based on field definition."""
        if not self.definition:
            return self.raw_value

        field_type = self.definition.field_type.upper()

        if field_type in ("INT", "LENGTH", "SEQNUM", "NUMINGROUP"):
            try:
                return int(self.raw_value)
            except ValueError:
                logger.debug(
                    "Cannot convert tag %d (%s) value '%s' to int",
                    self.tag, self.name, self.raw_value,
                )
                return self.raw_value

        if field_type in ("FLOAT", "PRICE", "QTY", "AMT", "PERCENTAGE", "PRICEOFFSET"):
            try:
                return float(self.raw_value)
            except ValueError:
                logger.debug(
                    "Cannot convert tag %d (%s) value '%s' to float",
                    self.tag, self.name, self.raw_value,
                )
                return self.raw_value

        if field_type == "BOOLEAN":
            return self.raw_value in ("Y", "1")

        return self.raw_value

    def to_dict(self) -> dict[str, Any]:
        """Convert the field to a dictionary representation."""
        result: dict[str, Any] = {
            "tag": self.tag,
            "name": self.name,
            "value": self.raw_value,
        }
        if self.value_description:
            result["value_description"] = self.value_description
        if self.description:
            result["field_description"] = self.description
        return result

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        value_desc = self.value_description
        if value_desc:
            return f"{self.name} ({self.tag}): {self.raw_value} ({value_desc})"
        return f"{self.name} ({self.tag}): {self.raw_value}"
