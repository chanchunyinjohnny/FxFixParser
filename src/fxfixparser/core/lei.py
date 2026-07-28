"""ISO 17442 Legal Entity Identifier (LEI) helpers.

Offline detection and check-digit validation of LEIs found in parsed FIX
messages, plus an on-demand lookup against the public GLEIF API (no API
key required). Only ``lookup_lei`` touches the network — detection and
validation are pure functions, so the parser core stays usable in
offline / restricted environments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from fxfixparser.core.message import FixMessage

# An LEI is 18 alphanumeric characters followed by 2 numeric check digits.
_LEI_FORMAT = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")

# Tags whose values may carry an LEI:
#   448  PartyID                 (PartyIDSource 447=N means LEI)
#   523  PartySubID              (e.g. Bloomberg PartySubIDType 4025)
#   785  SettlPartySubID
#   1121 RootPartySubID
#   1905 RegulatoryTradeIDSource (LEI of the UTI-generating entity)
LEI_BEARING_TAGS: tuple[int, ...] = (448, 523, 785, 1121, 1905)

GLEIF_API_URL = "https://api.gleif.org/api/v1/lei-records/{lei}"


class LeiLookupError(Exception):
    """Raised when a GLEIF lookup fails (network, HTTP or payload error)."""


@dataclass
class DetectedLei:
    """An LEI-formatted value found in a message, with where it was seen."""

    lei: str
    checksum_ok: bool = False
    source_tags: list[int] = field(default_factory=list)


def is_lei_candidate(value: str | None) -> bool:
    """Return True if the value has the ISO 17442 LEI format."""
    if not value:
        return False
    return bool(_LEI_FORMAT.match(value))


def is_valid_lei(value: str | None) -> bool:
    """Return True if the value is a well-formed LEI with valid check digits.

    Check digits are verified with ISO 7064 MOD 97-10 (as for IBANs):
    letters expand to two digits (A=10 .. Z=35) and the resulting number
    must be congruent to 1 modulo 97.
    """
    if not value or not is_lei_candidate(value):
        return False
    digits = "".join(str(int(char, 36)) for char in value)
    return int(digits) % 97 == 1


def find_leis(message: FixMessage) -> list[DetectedLei]:
    """Find unique LEI-formatted values in a parsed message.

    Scans the LEI-bearing party / regulatory tags across all venues and
    returns one entry per distinct LEI, in order of first appearance,
    with offline check-digit validation applied.
    """
    found: dict[str, DetectedLei] = {}
    for fix_field in message.fields:
        if fix_field.tag not in LEI_BEARING_TAGS:
            continue
        value = (fix_field.raw_value or "").strip()
        if not is_lei_candidate(value):
            continue
        entry = found.get(value)
        if entry is None:
            entry = DetectedLei(lei=value, checksum_ok=is_valid_lei(value))
            found[value] = entry
        if fix_field.tag not in entry.source_tags:
            entry.source_tags.append(fix_field.tag)
    return list(found.values())


def lookup_lei(lei: str, timeout: float = 6.0) -> dict[str, str]:
    """Look up an LEI on the public GLEIF API and return entity details.

    Returns a flat dict with ``lei``, ``legal_name``, ``status``,
    ``jurisdiction``, ``city``, ``country`` and ``registration_status``.

    Raises:
        LeiLookupError: on network failure, non-200 response, or an
            unexpected payload — with a message safe to show in the UI.
    """
    # Imported here so the parser core does not require requests at import
    # time; the UI is the only caller that needs the network.
    import requests

    url = GLEIF_API_URL.format(lei=lei)
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"Accept": "application/vnd.api+json"},
        )
    except requests.RequestException as exc:
        raise LeiLookupError(f"GLEIF request failed ({exc.__class__.__name__})") from exc

    if response.status_code == 404:
        raise LeiLookupError("not found in the GLEIF database")
    if response.status_code != 200:
        raise LeiLookupError(f"GLEIF returned HTTP {response.status_code}")

    try:
        attributes = response.json()["data"]["attributes"]
        entity = attributes["entity"]
    except (ValueError, KeyError, TypeError) as exc:
        raise LeiLookupError("unexpected GLEIF response payload") from exc

    legal_address = entity.get("legalAddress") or {}
    return {
        "lei": lei,
        "legal_name": (entity.get("legalName") or {}).get("name") or "",
        "status": entity.get("status") or "",
        "jurisdiction": entity.get("jurisdiction") or "",
        "city": legal_address.get("city") or "",
        "country": legal_address.get("country") or "",
        "registration_status": (attributes.get("registration") or {}).get("status") or "",
    }
