"""Parsed FIX report input format support.

Some vendor tools export FIX messages as a pretty-printed "parsed report"
instead of the raw wire format: one field per line shaped like
``(tag)FieldName: value``, repeating-group entries indented and separated
by ``----`` lines, and enum-decoded values rendered as ``LABEL (RAW)``
with the raw code in trailing parentheses. Tags are sorted numerically
within each section, so the original wire order is lost.

This module detects that layout and reconstructs a raw ``tag=value<SOH>``
stream so the normal parse pipeline can process it. Indentation and
separator lines carry no information the flat tag order doesn't already
carry, so they are dropped.

Known limitation: a free-text value that happens to end in
``singletoken (x)`` is indistinguishable from an enum decode and is
reduced to ``x``. No such field appears in observed reports.
"""

from __future__ import annotations

import re

from fxfixparser.core.exceptions import ParseError

SOH = "\x01"

# A report line: optional indentation, "(tag)", field name up to the
# first colon, then the display value.
_REPORT_LINE_RE = re.compile(r"^\s*\((\d+)\)([^:]*):(.*)$")

# A line that starts like a report field but fails the complete shape.
_FIELD_PREFIX_RE = re.compile(r"^\s*\(\d+\)")

# Group-entry separator lines: "----" (possibly indented).
_SEPARATOR_RE = re.compile(r"^\s*-{2,}\s*$")

# Enum decode: single-token label + trailing "(RAW)" code.
_ENUM_SUFFIX_RE = re.compile(r"^(?P<label>[A-Za-z0-9_./-]+) \((?P<raw>[A-Za-z0-9_./-]+)\)$")

_MIN_REPORT_LINES = 3
_MIN_REPORT_RATIO = 0.9
_MAX_TAG_DIGITS = 10


def looks_like_parsed_report(text: str) -> bool:
    """Return True when the text looks like a pretty-printed FIX report.

    Requires at least three report-shaped lines, and that report lines
    plus ``----`` separators make up >= 90% of the non-blank lines (a
    small tolerance for stray copy-paste lines, which conversion skips).
    Raw ``tag=value`` FIX text contains no report-shaped lines, so it can
    never match.
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    report_lines = sum(1 for line in lines if _REPORT_LINE_RE.match(line))
    if report_lines < _MIN_REPORT_LINES:
        return False
    separators = sum(1 for line in lines if _SEPARATOR_RE.match(line))
    return (report_lines + separators) / len(lines) >= _MIN_REPORT_RATIO


def parsed_report_to_raw(text: str) -> str:
    """Reconstruct a raw SOH-delimited FIX string from a parsed report."""
    pairs: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or _SEPARATOR_RE.match(line):
            continue
        match = _REPORT_LINE_RE.match(line)
        if match is None:
            if _FIELD_PREFIX_RE.match(line):
                raise ParseError(f"Malformed parsed report field on line {line_number}")
            continue  # stray copy-paste line
        tag_text = match.group(1)
        if len(tag_text) > _MAX_TAG_DIGITS:
            raise ParseError(f"Invalid tag number on line {line_number}")
        tag = int(tag_text)
        value = match.group(3).removeprefix(" ")
        enum_match = _ENUM_SUFFIX_RE.match(value)
        if enum_match is not None:
            value = enum_match.group("raw")
        pairs.append((tag, value))

    _restore_msg_type_position(pairs)
    return SOH.join(f"{tag}={value}" for tag, value in pairs) + SOH


def _restore_msg_type_position(pairs: list[tuple[int, str]]) -> None:
    """Move MsgType(35) to third position when displaced by numeric sorting.

    Reports sort tags numerically, so MsgSeqNum(34) lands before 35 and
    the header-order validation (8, 9, 35) would fail. Only reorders when
    the report starts with tags 8 and 9 as expected; otherwise the order
    is left for parse-time validation to report.
    """
    if len(pairs) < 3 or pairs[0][0] != 8 or pairs[1][0] != 9:
        return
    for index, (tag, _value) in enumerate(pairs):
        if tag == 35:
            if index > 2:
                pairs.insert(2, pairs.pop(index))
            return
