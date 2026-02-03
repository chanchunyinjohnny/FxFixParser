"""Unit tests for tag dictionary."""

import pytest

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.tags.dictionary import TagDictionary
from fxfixparser.tags.fix44 import FIX44_TAGS
from fxfixparser.tags.fx_tags import FX_CUSTOM_TAGS


class TestTagDictionary:
    """Tests for TagDictionary class."""

    def test_empty_dictionary(self) -> None:
        """Test empty dictionary."""
        d = TagDictionary()

        assert d.get(8) is None
        assert d.get_name(8) == "Unknown(8)"
        assert not d.has_tag(8)

    def test_add_and_get(self) -> None:
        """Test adding and retrieving definitions."""
        d = TagDictionary()
        defn = FixFieldDefinition(tag=55, name="Symbol", field_type="STRING")
        d.add(defn)

        assert d.has_tag(55)
        assert d.get(55) == defn
        assert d.get_name(55) == "Symbol"

    def test_all_tags(self) -> None:
        """Test getting all tag numbers."""
        d = TagDictionary()
        d.add(FixFieldDefinition(tag=8, name="BeginString"))
        d.add(FixFieldDefinition(tag=35, name="MsgType"))

        tags = d.all_tags()
        assert 8 in tags
        assert 35 in tags

    def test_merge_dictionaries(self) -> None:
        """Test merging two dictionaries."""
        d1 = TagDictionary()
        d1.add(FixFieldDefinition(tag=8, name="BeginString"))

        d2 = TagDictionary()
        d2.add(FixFieldDefinition(tag=35, name="MsgType"))

        d1.merge(d2)

        assert d1.has_tag(8)
        assert d1.has_tag(35)

    def test_default_dictionary(self, tag_dictionary: TagDictionary) -> None:
        """Test default dictionary contains standard tags."""
        # Check common FIX 4.4 tags
        assert tag_dictionary.has_tag(8)  # BeginString
        assert tag_dictionary.has_tag(9)  # BodyLength
        assert tag_dictionary.has_tag(35)  # MsgType
        assert tag_dictionary.has_tag(10)  # CheckSum
        assert tag_dictionary.has_tag(55)  # Symbol
        assert tag_dictionary.has_tag(54)  # Side

    def test_tag_names(self, tag_dictionary: TagDictionary) -> None:
        """Test tag name resolution."""
        assert tag_dictionary.get_name(8) == "BeginString"
        assert tag_dictionary.get_name(35) == "MsgType"
        assert tag_dictionary.get_name(55) == "Symbol"

    def test_enumerated_values(self, tag_dictionary: TagDictionary) -> None:
        """Test enumerated value descriptions."""
        side_defn = tag_dictionary.get(54)
        assert side_defn is not None
        assert side_defn.get_value_description("1") == "Buy"
        assert side_defn.get_value_description("2") == "Sell"

        msg_type_defn = tag_dictionary.get(35)
        assert msg_type_defn is not None
        assert msg_type_defn.get_value_description("8") == "ExecutionReport"
        assert msg_type_defn.get_value_description("D") == "NewOrderSingle"


class TestFIX44Tags:
    """Tests for FIX 4.4 tag definitions."""

    def test_fix44_tags_not_empty(self) -> None:
        """Test FIX 4.4 tags list is not empty."""
        assert len(FIX44_TAGS) > 0

    def test_required_header_tags(self) -> None:
        """Test required header tags are defined."""
        tag_numbers = {t.tag for t in FIX44_TAGS}

        assert 8 in tag_numbers  # BeginString
        assert 9 in tag_numbers  # BodyLength
        assert 35 in tag_numbers  # MsgType
        assert 49 in tag_numbers  # SenderCompID
        assert 56 in tag_numbers  # TargetCompID

    def test_trailer_tag(self) -> None:
        """Test trailer tag is defined."""
        tag_numbers = {t.tag for t in FIX44_TAGS}
        assert 10 in tag_numbers  # CheckSum


class TestFXCustomTags:
    """Tests for FX-specific custom tags."""

    def test_fx_tags_not_empty(self) -> None:
        """Test FX custom tags list is not empty."""
        assert len(FX_CUSTOM_TAGS) > 0

    def test_options_tags(self) -> None:
        """Test options-related tags are defined."""
        tag_numbers = {t.tag for t in FX_CUSTOM_TAGS}

        assert 201 in tag_numbers  # PutOrCall
        assert 202 in tag_numbers  # StrikePrice
