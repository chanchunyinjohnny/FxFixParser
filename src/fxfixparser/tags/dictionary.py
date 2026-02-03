"""Tag dictionary manager for FIX field definitions."""

from fxfixparser.core.field import FixFieldDefinition


class TagDictionary:
    """Manages FIX field definitions and lookups."""

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
        """Create a default dictionary with FIX 4.4 and FX-specific tags."""
        from fxfixparser.tags.fix44 import FIX44_TAGS
        from fxfixparser.tags.fx_tags import FX_CUSTOM_TAGS

        dictionary = cls()
        for definition in FIX44_TAGS:
            dictionary.add(definition)
        for definition in FX_CUSTOM_TAGS:
            dictionary.add(definition)
        return dictionary
