"""Unit tests for repeating groups functionality."""

import pytest

from fxfixparser.core.field import FixField, FixFieldDefinition
from fxfixparser.core.message import FixMessage, RepeatingGroup, RepeatingGroupEntry
from fxfixparser.tags.repeating_groups import (
    REPEATING_GROUPS,
    RepeatingGroupDefinition,
    get_group_definition,
    is_count_tag,
)


class TestRepeatingGroupDefinitions:
    """Tests for repeating group definitions."""

    def test_market_data_group_defined(self) -> None:
        """Test that NoMDEntries group is defined."""
        group = get_group_definition(268)
        assert group is not None
        assert group.name == "Market Data Entries"
        assert 269 in group.member_tags  # MDEntryType
        assert 270 in group.member_tags  # MDEntryPx
        assert 271 in group.member_tags  # MDEntrySize

    def test_market_data_group_includes_forward_tags(self) -> None:
        """Test that NoMDEntries group includes forward-specific tags 1026/1027."""
        group = get_group_definition(268)
        assert group is not None
        assert 1026 in group.member_tags  # MDEntrySpotRate
        assert 1027 in group.member_tags  # MDEntryForwardPoints

    def test_party_ids_group_defined(self) -> None:
        """Test that NoPartyIDs group is defined."""
        group = get_group_definition(453)
        assert group is not None
        assert group.name == "Party IDs"
        assert 448 in group.member_tags  # PartyID
        assert 447 in group.member_tags  # PartyIDSource
        assert 452 in group.member_tags  # PartyRole

    def test_related_sym_group_defined(self) -> None:
        """Test that NoRelatedSym group is defined."""
        group = get_group_definition(146)
        assert group is not None
        assert group.name == "Related Symbols"
        assert 55 in group.member_tags  # Symbol

    def test_related_sym_group_includes_lfx_swap_tags(self) -> None:
        """Test that NoRelatedSym group includes LFX custom tags for swaps."""
        group = get_group_definition(146)
        assert group is not None
        # Standard FX swap tags
        assert 63 in group.member_tags   # SettlType (near leg)
        assert 64 in group.member_tags   # SettlDate (near leg)
        assert 192 in group.member_tags  # OrderQty2 (far leg quantity)
        assert 193 in group.member_tags  # SettlDate2 (far leg date)
        # LFX custom tag for far leg tenor
        assert 8004 in group.member_tags  # SettlType2 (Far Leg Tenor)

    def test_unknown_group_returns_none(self) -> None:
        """Test that unknown count tag returns None."""
        group = get_group_definition(9999)
        assert group is None

    def test_is_count_tag(self) -> None:
        """Test is_count_tag function."""
        assert is_count_tag(268) is True  # NoMDEntries
        assert is_count_tag(453) is True  # NoPartyIDs
        assert is_count_tag(146) is True  # NoRelatedSym
        assert is_count_tag(55) is False  # Symbol (not a count tag)
        assert is_count_tag(9999) is False  # Unknown tag


class TestLFXForwardMDGrouping:
    """Tests for MD entry grouping with LFX forward market data (tags 1026/1027)."""

    def test_forward_md_entries_grouped_with_spot_rate_and_fwd_points(self) -> None:
        """Test that tags 1026/1027 are grouped within MD entries, not split out."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=35, raw_value="X"),
            FixField(tag=268, raw_value="2"),   # NoMDEntries = 2
            FixField(tag=279, raw_value="1"),   # MDUpdateAction
            FixField(tag=269, raw_value="0"),   # MDEntryType = Bid
            FixField(tag=270, raw_value="1.180603"),  # MDEntryPx (all-in)
            FixField(tag=290, raw_value="0"),   # MDEntryPositionNo
            FixField(tag=1026, raw_value="1.17905"),  # MDEntrySpotRate
            FixField(tag=1027, raw_value="0.001553"),  # MDEntryForwardPoints
            FixField(tag=279, raw_value="1"),   # MDUpdateAction (entry 2)
            FixField(tag=269, raw_value="1"),   # MDEntryType = Offer
            FixField(tag=270, raw_value="1.180668"),
            FixField(tag=290, raw_value="0"),
            FixField(tag=1026, raw_value="1.17911"),
            FixField(tag=1027, raw_value="0.001558"),
            FixField(tag=10, raw_value="043"),
        ]
        message = FixMessage(fields=fields)

        structured = message.get_structured_fields()
        groups = [sf for sf in structured if sf.is_group]
        assert len(groups) == 1

        group = groups[0].group
        assert group is not None
        assert group.count == 2
        assert len(group.entries) == 2

        # Each entry should have 5 fields (279, 269, 270, 290, 1026, 1027)
        # but 279 is the first tag so entry boundary is on 279
        entry1 = group.entries[0]
        entry1_tags = [f.tag for f in entry1.fields]
        assert 1026 in entry1_tags, "Tag 1026 missing from entry 1"
        assert 1027 in entry1_tags, "Tag 1027 missing from entry 1"

        entry2 = group.entries[1]
        entry2_tags = [f.tag for f in entry2.fields]
        assert 1026 in entry2_tags, "Tag 1026 missing from entry 2"
        assert 1027 in entry2_tags, "Tag 1027 missing from entry 2"


class TestRepeatingGroupEntry:
    """Tests for RepeatingGroupEntry class."""

    def test_entry_creation(self) -> None:
        """Test creating a group entry."""
        fields = [
            FixField(tag=269, raw_value="0"),
            FixField(tag=270, raw_value="1.0850"),
        ]
        entry = RepeatingGroupEntry(index=1, fields=fields)

        assert entry.index == 1
        assert len(entry.fields) == 2

    def test_entry_to_dict(self) -> None:
        """Test entry to_dict conversion."""
        fields = [FixField(tag=269, raw_value="0")]
        entry = RepeatingGroupEntry(index=1, fields=fields)

        d = entry.to_dict()
        assert d["index"] == 1
        assert len(d["fields"]) == 1


class TestRepeatingGroup:
    """Tests for RepeatingGroup class."""

    def test_group_creation(self) -> None:
        """Test creating a repeating group."""
        count_field = FixField(tag=268, raw_value="2")
        group = RepeatingGroup(name="Market Data Entries", count_field=count_field)

        assert group.name == "Market Data Entries"
        assert group.count == 2
        assert len(group.entries) == 0

    def test_group_with_entries(self) -> None:
        """Test group with entries."""
        count_field = FixField(tag=268, raw_value="2")
        entries = [
            RepeatingGroupEntry(index=1, fields=[FixField(tag=269, raw_value="0")]),
            RepeatingGroupEntry(index=2, fields=[FixField(tag=269, raw_value="1")]),
        ]
        group = RepeatingGroup(
            name="Market Data Entries",
            count_field=count_field,
            entries=entries,
        )

        assert group.count == 2
        assert len(group.entries) == 2

    def test_group_to_dict(self) -> None:
        """Test group to_dict conversion."""
        count_field = FixField(tag=268, raw_value="1")
        entries = [
            RepeatingGroupEntry(index=1, fields=[FixField(tag=269, raw_value="0")]),
        ]
        group = RepeatingGroup(
            name="Market Data Entries",
            count_field=count_field,
            entries=entries,
        )

        d = group.to_dict()
        assert d["name"] == "Market Data Entries"
        assert d["count_tag"] == 268
        assert d["count"] == 1
        assert len(d["entries"]) == 1


class TestFixMessageStructuredFields:
    """Tests for FixMessage.get_structured_fields method."""

    def test_message_without_groups(self) -> None:
        """Test message without repeating groups."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=35, raw_value="8"),
            FixField(tag=55, raw_value="EUR/USD"),
        ]
        message = FixMessage(fields=fields)

        structured = message.get_structured_fields()
        assert len(structured) == 3
        assert all(not sf.is_group for sf in structured)

    def test_message_with_market_data_group(self) -> None:
        """Test message with market data repeating group."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=35, raw_value="W"),
            FixField(tag=55, raw_value="EUR/USD"),
            FixField(tag=268, raw_value="2"),  # NoMDEntries
            FixField(tag=269, raw_value="0"),  # MDEntryType - Bid
            FixField(tag=270, raw_value="1.0850"),  # MDEntryPx
            FixField(tag=269, raw_value="1"),  # MDEntryType - Offer
            FixField(tag=270, raw_value="1.0852"),  # MDEntryPx
            FixField(tag=10, raw_value="123"),
        ]
        message = FixMessage(fields=fields)

        structured = message.get_structured_fields()

        # Should have: 3 regular fields + 1 group + 1 checksum
        groups = [sf for sf in structured if sf.is_group]
        assert len(groups) == 1

        group = groups[0].group
        assert group is not None
        assert group.name == "Market Data Entries"
        assert group.count == 2
        assert len(group.entries) == 2

        # Check first entry
        assert group.entries[0].index == 1
        assert len(group.entries[0].fields) == 2
        assert group.entries[0].fields[0].raw_value == "0"  # Bid

        # Check second entry
        assert group.entries[1].index == 2
        assert group.entries[1].fields[0].raw_value == "1"  # Offer

    def test_message_to_dict_structured(self) -> None:
        """Test to_dict with structured output."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=35, raw_value="W"),
            FixField(tag=268, raw_value="1"),
            FixField(tag=269, raw_value="0"),
            FixField(tag=270, raw_value="1.0850"),
        ]
        message = FixMessage(fields=fields)

        d = message.to_dict(structured=True)
        assert "fields" in d

        # Find the group in fields
        group_dict = None
        for f in d["fields"]:
            if "entries" in f:
                group_dict = f
                break

        assert group_dict is not None
        assert group_dict["name"] == "Market Data Entries"
        assert group_dict["count"] == 1

    def test_message_to_dict_flat(self) -> None:
        """Test to_dict with flat output."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=268, raw_value="1"),
            FixField(tag=269, raw_value="0"),
        ]
        message = FixMessage(fields=fields)

        d = message.to_dict(structured=False)
        assert len(d["fields"]) == 3
        # All should be flat field dicts, no entries
        assert all("entries" not in f for f in d["fields"])

    def test_message_to_human_readable_structured(self) -> None:
        """Test to_human_readable with structured output."""
        defn_268 = FixFieldDefinition(tag=268, name="NoMDEntries", field_type="NUMINGROUP")
        defn_269 = FixFieldDefinition(tag=269, name="MDEntryType", field_type="CHAR")
        defn_270 = FixFieldDefinition(tag=270, name="MDEntryPx", field_type="PRICE")

        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=35, raw_value="W"),
            FixField(tag=268, raw_value="2", definition=defn_268),
            FixField(tag=269, raw_value="0", definition=defn_269),
            FixField(tag=270, raw_value="1.0850", definition=defn_270),
            FixField(tag=269, raw_value="1", definition=defn_269),
            FixField(tag=270, raw_value="1.0852", definition=defn_270),
        ]
        message = FixMessage(fields=fields)

        output = message.to_human_readable(structured=True)

        assert "NoMDEntries" in output
        assert "Market Data Entries" in output
        assert "[Entry 1]" in output
        assert "[Entry 2]" in output
        assert "1.0850" in output
        assert "1.0852" in output

    def test_message_to_human_readable_flat(self) -> None:
        """Test to_human_readable with flat output."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=268, raw_value="1"),
            FixField(tag=269, raw_value="0"),
        ]
        message = FixMessage(fields=fields)

        output = message.to_human_readable(structured=False)

        # Should not have entry markers
        assert "[Entry" not in output
