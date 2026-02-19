"""Unit tests for the FIX specification XML loader."""

from pathlib import Path

from fxfixparser.spec.loader import load_fix44_fields, load_fix_spec_fields
from fxfixparser.tags.dictionary import TagDictionary


class TestFIX44XMLLoader:
    """Tests for FIX44.xml loading."""

    def test_loads_fields_from_xml(self) -> None:
        """Test that fields are loaded from the XML spec."""
        fields = load_fix44_fields()
        assert len(fields) > 0

    def test_loads_standard_header_tags(self) -> None:
        """Test that standard header tags are present."""
        fields_by_tag = {f.tag: f for f in load_fix44_fields()}

        assert 8 in fields_by_tag  # BeginString
        assert 9 in fields_by_tag  # BodyLength
        assert 35 in fields_by_tag  # MsgType
        assert 49 in fields_by_tag  # SenderCompID
        assert 56 in fields_by_tag  # TargetCompID

    def test_loads_enumerated_values(self) -> None:
        """Test that enumerated values are parsed from XML."""
        fields_by_tag = {f.tag: f for f in load_fix44_fields()}

        # MsgType (tag 35) has many enum values
        msg_type = fields_by_tag[35]
        assert len(msg_type.valid_values) > 0
        assert "0" in msg_type.valid_values  # Heartbeat
        assert "8" in msg_type.valid_values  # ExecutionReport

        # Side (tag 54) has enum values
        side = fields_by_tag[54]
        assert "1" in side.valid_values  # Buy
        assert "2" in side.valid_values  # Sell

    def test_loads_field_types(self) -> None:
        """Test that field types are correctly parsed."""
        fields_by_tag = {f.tag: f for f in load_fix44_fields()}

        assert fields_by_tag[8].field_type == "STRING"
        assert fields_by_tag[9].field_type == "LENGTH"
        assert fields_by_tag[34].field_type == "SEQNUM"
        assert fields_by_tag[44].field_type == "PRICE"
        assert fields_by_tag[38].field_type == "QTY"

    def test_covers_repeating_group_member_tags(self) -> None:
        """Test that all tags referenced in repeating groups are now defined."""
        from fxfixparser.tags.repeating_groups import REPEATING_GROUPS

        dictionary = TagDictionary.default()
        missing_tags: list[int] = []

        for group in REPEATING_GROUPS:
            for tag in group.member_tags:
                if not dictionary.has_tag(tag):
                    missing_tags.append(tag)

        assert missing_tags == [], (
            f"Tags referenced in repeating groups but not defined: {missing_tags}"
        )

    def test_xml_tags_count(self) -> None:
        """Test that a reasonable number of tags are loaded from XML."""
        fields = load_fix44_fields()
        # FIX 4.4 has ~900+ fields
        assert len(fields) > 800

    def test_missing_xml_returns_empty(self) -> None:
        """Test that a missing XML file returns an empty list."""
        fields = load_fix44_fields(Path("/nonexistent/FIX44.xml"))
        assert fields == []

    def test_default_dictionary_has_xml_tags(self) -> None:
        """Test that default dictionary includes XML-sourced tags."""
        dictionary = TagDictionary.default()

        # These tags are from XML only (not in manually-curated fix44.py)
        # Tag 67 (ListSeqNo) is used in repeating_groups but wasn't in fix44.py
        assert dictionary.has_tag(67)
        assert dictionary.has_tag(79)  # AllocAccount
        assert dictionary.has_tag(80)  # AllocQty

    def test_curated_tags_override_xml(self) -> None:
        """Test that manually-curated tags override XML tags with richer descriptions."""
        dictionary = TagDictionary.default()

        # Tag 55 (Symbol) should have the curated FX-specific description
        symbol = dictionary.get(55)
        assert symbol is not None
        assert "currency pair" in symbol.description.lower()


class TestLoadFixSpecFields:
    """Tests for the generic load_fix_spec_fields function."""

    def test_load_nonexistent_file_returns_empty(self) -> None:
        """Test that loading a nonexistent file returns an empty list."""
        fields = load_fix_spec_fields(Path("/nonexistent/spec.xml"))
        assert fields == []

    def test_load_fix44_fields_still_works(self) -> None:
        """Test backward compatibility: load_fix44_fields() still returns fields."""
        fields = load_fix44_fields()
        assert len(fields) > 0
