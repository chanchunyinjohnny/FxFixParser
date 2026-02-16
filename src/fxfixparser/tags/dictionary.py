"""Tag dictionary manager for FIX field definitions."""

import logging

from fxfixparser.core.field import FixFieldDefinition

logger = logging.getLogger(__name__)


class TagDictionary:
    """Manages FIX field definitions and lookups."""

    _default_instance: "TagDictionary | None" = None

    def __init__(self) -> None:
        self._tags: dict[int, FixFieldDefinition] = {}

    def add(self, definition: FixFieldDefinition) -> None:
        """Add a field definition to the dictionary."""
        self._tags[definition.tag] = definition

    def get(self, tag: int) -> FixFieldDefinition | None:
        """Get the definition for a tag number."""
        return self._tags.get(tag)

    def get_name(self, tag: int) -> str:
        """Get the name for a tag number, or 'Unknown' if not defined."""
        definition = self.get(tag)
        if definition:
            return definition.name
        return f"Unknown({tag})"

    def has_tag(self, tag: int) -> bool:
        """Check if a tag is defined in the dictionary."""
        return tag in self._tags

    def all_tags(self) -> list[int]:
        """Get all defined tag numbers."""
        return list(self._tags.keys())

    def merge(self, other: "TagDictionary") -> None:
        """Merge another dictionary into this one."""
        for tag, definition in other._tags.items():
            self._tags[tag] = definition

    @classmethod
    def default(cls) -> "TagDictionary":
        """Return a cached default dictionary with FIX 4.4 and FX-specific tags.

        The result is built once and cached at class level to avoid
        re-parsing the FIX44.xml spec on every call.

        Loads tags in priority order (later entries override earlier ones):
        1. FIX44.xml spec (comprehensive base with all standard tags)
        2. Manually-curated FIX 4.4 tags (better descriptions for FX fields)
        3. FX-specific custom tags (vendor and FX-specific extensions)
        """
        if cls._default_instance is not None:
            return cls._default_instance

        from fxfixparser.spec.loader import load_fix44_fields
        from fxfixparser.tags.fix44 import FIX44_TAGS
        from fxfixparser.tags.fx_tags import FX_CUSTOM_TAGS

        dictionary = cls()

        # 1. Load all standard tags from the XML spec as a comprehensive base
        xml_fields = load_fix44_fields()
        for definition in xml_fields:
            dictionary.add(definition)

        # 2. Override with manually-curated tags (richer FX-focused descriptions)
        for definition in FIX44_TAGS:
            dictionary.add(definition)

        # 3. Add FX-specific custom tags
        for definition in FX_CUSTOM_TAGS:
            dictionary.add(definition)

        cls._default_instance = dictionary
        return dictionary
