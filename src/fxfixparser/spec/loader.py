"""FIX specification XML loader.

Parses QuickFIX-format XML specification files and generates
FixFieldDefinition objects for use in the tag dictionary.
Supports any QuickFIX XML (FIX44.xml, FIX50SP2.xml, etc.).
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from fxfixparser.core.field import FixFieldDefinition

logger = logging.getLogger(__name__)

_SPEC_DIR = Path(__file__).parent
_FIX44_XML = _SPEC_DIR / "FIX44.xml"


def load_fix_spec_fields(xml_path: Path) -> list[FixFieldDefinition]:
    """Load field definitions from any QuickFIX-format XML specification.

    Parses a QuickFIX XML file with the standard ``<fix><fields><field>``
    structure and returns a list of :class:`FixFieldDefinition` objects.

    Args:
        xml_path: Path to the QuickFIX XML specification file.

    Returns:
        A list of FixFieldDefinition objects for all fields in the spec.
        Returns an empty list if the file does not exist or contains no
        ``<fields>`` element.
    """
    if not xml_path.exists():
        logger.warning("Spec XML not found at %s, returning empty list", xml_path)
        return []

    tree = ET.parse(xml_path)  # noqa: S314
    root = tree.getroot()

    fields_elem = root.find("fields")
    if fields_elem is None:
        logger.warning("No <fields> element found in %s", xml_path)
        return []

    definitions: list[FixFieldDefinition] = []
    for field_elem in fields_elem.findall("field"):
        tag_str = field_elem.get("number")
        name = field_elem.get("name")
        field_type = field_elem.get("type", "STRING")

        if not tag_str or not name:
            continue

        try:
            tag = int(tag_str)
        except ValueError:
            continue

        # Parse enumerated values
        valid_values: dict[str, str] = {}
        for value_elem in field_elem.findall("value"):
            enum_val = value_elem.get("enum")
            description = value_elem.get("description", "")
            if enum_val is not None:
                valid_values[enum_val] = description

        definitions.append(
            FixFieldDefinition(
                tag=tag,
                name=name,
                field_type=field_type,
                valid_values=valid_values,
            )
        )

    logger.info("Loaded %d field definitions from %s", len(definitions), xml_path)
    return definitions


def load_fix44_fields(xml_path: Path | None = None) -> list[FixFieldDefinition]:
    """Load field definitions from the FIX 4.4 XML specification.

    This is a convenience wrapper around :func:`load_fix_spec_fields` that
    defaults to the bundled FIX44.xml file.

    Args:
        xml_path: Path to the FIX44.xml file. Defaults to the bundled spec.

    Returns:
        A list of FixFieldDefinition objects for all fields in the spec.
    """
    path = xml_path or _FIX44_XML
    return load_fix_spec_fields(path)
