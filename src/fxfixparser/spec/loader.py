"""FIX 4.4 specification XML loader.

Parses the official FIX44.xml specification file and generates
FixFieldDefinition objects for use in the tag dictionary.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from fxfixparser.core.field import FixFieldDefinition

logger = logging.getLogger(__name__)

_SPEC_DIR = Path(__file__).parent
_FIX44_XML = _SPEC_DIR / "FIX44.xml"


def load_fix44_fields(xml_path: Path | None = None) -> list[FixFieldDefinition]:
    """Load field definitions from the FIX 4.4 XML specification.

    Args:
        xml_path: Path to the FIX44.xml file. Defaults to the bundled spec.

    Returns:
        A list of FixFieldDefinition objects for all fields in the spec.
    """
    path = xml_path or _FIX44_XML
    if not path.exists():
        logger.warning("FIX44.xml not found at %s, returning empty list", path)
        return []

    tree = ET.parse(path)  # noqa: S314
    root = tree.getroot()

    fields_elem = root.find("fields")
    if fields_elem is None:
        logger.warning("No <fields> element found in %s", path)
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

    logger.info("Loaded %d field definitions from %s", len(definitions), path)
    return definitions
