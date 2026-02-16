"""FIX message data models."""

import logging
from dataclasses import dataclass, field
from typing import Any, Iterator

from fxfixparser.core.field import FixField
from fxfixparser.tags.repeating_groups import get_group_definition

logger = logging.getLogger(__name__)


@dataclass
class RepeatingGroupEntry:
    """A single entry within a repeating group."""

    index: int  # 1-based index within the group
    fields: list[FixField] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the entry to a dictionary representation."""
        return {
            "index": self.index,
            "fields": [f.to_dict() for f in self.fields],
        }


@dataclass
class RepeatingGroup:
    """A repeating group with its count field and entries."""

    name: str
    count_field: FixField
    entries: list[RepeatingGroupEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Get the declared number of entries in this group."""
        try:
            return int(self.count_field.raw_value)
        except ValueError:
            logger.warning(
                "Non-numeric group count for %s (tag %d): '%s'",
                self.name, self.count_field.tag, self.count_field.raw_value,
            )
            return 0

    def to_dict(self) -> dict[str, Any]:
        """Convert the group to a dictionary representation."""
        return {
            "name": self.name,
            "count_tag": self.count_field.tag,
            "count_tag_name": self.count_field.name,
            "count": self.count,
            "entries": [e.to_dict() for e in self.entries],
        }


@dataclass
class StructuredField:
    """A field that may be standalone or part of a group."""

    field: FixField | None = None
    group: RepeatingGroup | None = None

    @property
    def is_group(self) -> bool:
        """Check if this is a repeating group."""
        return self.group is not None


@dataclass
class FixMessage:
    """A parsed FIX message containing all fields."""

    fields: list[FixField] = field(default_factory=list)
    raw_message: str = ""
    venue: str | None = None
    product_type: str | None = None

    def get_field(self, tag: int) -> FixField | None:
        """Get the first field with the given tag number."""
        for f in self.fields:
            if f.tag == tag:
                return f
        return None

    def get_fields(self, tag: int) -> list[FixField]:
        """Get all fields with the given tag number."""
        return [f for f in self.fields if f.tag == tag]

    def get_value(self, tag: int) -> str | None:
        """Get the raw value of the first field with the given tag number."""
        f = self.get_field(tag)
        return f.raw_value if f else None

    @property
    def begin_string(self) -> str | None:
        """Get the BeginString (tag 8) value."""
        return self.get_value(8)

    @property
    def body_length(self) -> int | None:
        """Get the BodyLength (tag 9) value."""
        value = self.get_value(9)
        if value:
            try:
                return int(value)
            except ValueError:
                return None
        return None

    @property
    def msg_type(self) -> str | None:
        """Get the MsgType (tag 35) value."""
        return self.get_value(35)

    @property
    def sender_comp_id(self) -> str | None:
        """Get the SenderCompID (tag 49) value."""
        return self.get_value(49)

    @property
    def target_comp_id(self) -> str | None:
        """Get the TargetCompID (tag 56) value."""
        return self.get_value(56)

    @property
    def checksum(self) -> str | None:
        """Get the CheckSum (tag 10) value."""
        return self.get_value(10)

    def __iter__(self) -> Iterator[FixField]:
        """Iterate over all fields in the message."""
        return iter(self.fields)

    def __len__(self) -> int:
        """Return the number of fields in the message."""
        return len(self.fields)

    def get_structured_fields(self) -> list[StructuredField]:
        """Get fields organized into a structured format with repeating groups.

        This method analyzes the flat field list and organizes repeating groups
        into a hierarchical structure for better display.

        Entry boundaries are detected when a member tag that has already been
        seen in the current entry appears again, indicating the start of a
        new entry.

        Returns:
            A list of StructuredField objects, where each may be either a
            standalone field or a repeating group containing multiple entries.
        """
        result: list[StructuredField] = []
        i = 0

        while i < len(self.fields):
            current_field = self.fields[i]
            group_def = get_group_definition(current_field.tag)

            if group_def is not None:
                # This is a repeating group count tag
                try:
                    count = int(current_field.raw_value)
                except ValueError:
                    logger.warning(
                        "Non-numeric group count for tag %d: '%s'",
                        current_field.tag, current_field.raw_value,
                    )
                    count = 0

                group = RepeatingGroup(
                    name=group_def.name,
                    count_field=current_field,
                    entries=[],
                )

                # Collect group entries
                i += 1
                entry_index = 1
                current_entry: list[FixField] = []
                seen_tags: set[int] = set()

                while i < len(self.fields) and entry_index <= count:
                    fld = self.fields[i]

                    if fld.tag in group_def.member_tags:
                        # Detect entry boundary: if we've already seen this
                        # tag in the current entry, it marks a new entry
                        if current_entry and fld.tag in seen_tags:
                            # Save previous entry and start new one
                            group.entries.append(
                                RepeatingGroupEntry(
                                    index=entry_index,
                                    fields=current_entry,
                                )
                            )
                            entry_index += 1
                            current_entry = [fld]
                            seen_tags = {fld.tag}
                        else:
                            current_entry.append(fld)
                            seen_tags.add(fld.tag)
                        i += 1
                    else:
                        # Not a member tag - end of group entries
                        break

                # Save last entry
                if current_entry:
                    group.entries.append(
                        RepeatingGroupEntry(
                            index=entry_index,
                            fields=current_entry,
                        )
                    )

                # Validate actual vs declared count
                actual_count = len(group.entries)
                if count > 0 and actual_count != count:
                    logger.warning(
                        "Group '%s' (tag %d) declared %d entries but found %d",
                        group_def.name, current_field.tag, count, actual_count,
                    )

                result.append(StructuredField(group=group))
            else:
                # Regular field
                result.append(StructuredField(field=current_field))
                i += 1

        return result

    def to_dict(self, structured: bool = True) -> dict[str, Any]:
        """Convert the message to a dictionary representation.

        Args:
            structured: If True, organize repeating groups into nested structures.
                       If False, return a flat list of fields.

        Returns:
            Dictionary representation of the message.
        """
        base = {
            "begin_string": self.begin_string,
            "msg_type": self.msg_type,
            "sender_comp_id": self.sender_comp_id,
            "target_comp_id": self.target_comp_id,
            "venue": self.venue,
            "product_type": self.product_type,
        }

        if structured:
            structured_fields = self.get_structured_fields()
            fields_list: list[dict[str, Any]] = []
            for sf in structured_fields:
                if sf.is_group and sf.group:
                    fields_list.append(sf.group.to_dict())
                elif sf.field:
                    fields_list.append(sf.field.to_dict())
            base["fields"] = fields_list
        else:
            base["fields"] = [f.to_dict() for f in self.fields]

        return base

    def to_human_readable(self, structured: bool = True) -> str:
        """Convert the message to a human-readable string.

        Args:
            structured: If True, show repeating groups with visual hierarchy.
                       If False, show a flat list of fields.

        Returns:
            Human-readable string representation.
        """
        lines = []
        lines.append(f"FIX Message: {self.begin_string or 'Unknown'}")
        lines.append(f"Message Type: {self.msg_type or 'Unknown'}")
        if self.venue:
            lines.append(f"Venue: {self.venue}")
        if self.product_type:
            lines.append(f"Product Type: {self.product_type}")
        lines.append("-" * 50)

        if structured:
            structured_fields = self.get_structured_fields()
            for sf in structured_fields:
                if sf.is_group and sf.group:
                    group = sf.group
                    lines.append(f"\n{group.count_field.name} ({group.count_field.tag}): {group.count} - {group.name}")
                    lines.append("=" * 40)
                    for entry in group.entries:
                        lines.append(f"  [Entry {entry.index}]")
                        for f in entry.fields:
                            lines.append(f"    {f}")
                    lines.append("")
                elif sf.field:
                    lines.append(str(sf.field))
        else:
            for f in self.fields:
                lines.append(str(f))

        return "\n".join(lines)


@dataclass
class ParsedTrade:
    """High-level trade information extracted from a FIX message."""

    symbol: str | None = None
    side: str | None = None
    quantity: float | None = None
    price: float | None = None
    currency: str | None = None
    settlement_date: str | None = None
    venue: str | None = None
    product_type: str | None = None
    order_id: str | None = None
    exec_id: str | None = None
    trade_date: str | None = None
    counter_currency: str | None = None
    settlement_currency: str | None = None

    # Quote-specific fields
    bid_price: float | None = None
    offer_price: float | None = None
    bid_size: float | None = None
    offer_size: float | None = None
    bid_spot_rate: float | None = None
    offer_spot_rate: float | None = None
    bid_fwd_points: float | None = None
    offer_fwd_points: float | None = None

    # Swap-specific fields (far leg)
    far_settlement_date: str | None = None
    far_bid_fwd_points: float | None = None
    far_offer_fwd_points: float | None = None
    bid_swap_points: float | None = None
    offer_swap_points: float | None = None
    near_leg_bid_rate: float | None = None
    near_leg_offer_rate: float | None = None
    far_leg_bid_rate: float | None = None
    far_leg_offer_rate: float | None = None

    # Message type indicator
    is_quote: bool = False
    is_swap: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert the trade to a dictionary representation."""
        result = {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "currency": self.currency,
            "settlement_date": self.settlement_date,
            "venue": self.venue,
            "product_type": self.product_type,
            "order_id": self.order_id,
            "exec_id": self.exec_id,
            "trade_date": self.trade_date,
            "counter_currency": self.counter_currency,
            "settlement_currency": self.settlement_currency,
        }
        if self.is_quote:
            result.update({
                "bid_price": self.bid_price,
                "offer_price": self.offer_price,
                "bid_size": self.bid_size,
                "offer_size": self.offer_size,
                "bid_spot_rate": self.bid_spot_rate,
                "offer_spot_rate": self.offer_spot_rate,
                "bid_fwd_points": self.bid_fwd_points,
                "offer_fwd_points": self.offer_fwd_points,
            })
        if self.is_swap:
            result.update({
                "far_settlement_date": self.far_settlement_date,
                "far_bid_fwd_points": self.far_bid_fwd_points,
                "far_offer_fwd_points": self.far_offer_fwd_points,
                "bid_swap_points": self.bid_swap_points,
                "offer_swap_points": self.offer_swap_points,
            })
        return result
