"""Unit tests for LEI detection, validation and GLEIF lookup."""

import pytest
import requests

from fxfixparser.core.field import FixField
from fxfixparser.core.lei import (
    LeiLookupError,
    find_leis,
    is_lei_candidate,
    is_valid_lei,
    lookup_lei,
)
from fxfixparser.core.message import FixMessage
from fxfixparser.core.parser import FixParser, ParserConfig
from tests.fixtures.sample_messages import BLOOMBERG_MAP_SWAP_EXEC


class TestLeiValidation:
    """Tests for offline LEI format and check-digit validation."""

    def test_valid_leis_pass_check_digits(self) -> None:
        """GLEIF-issued identifiers must pass ISO 7064 MOD 97-10."""
        assert is_valid_lei("54930035WQZLGC45RZ35")
        assert is_valid_lei("254900HSS82AHMTPAD95")
        assert is_valid_lei("KNPC1X7GHDZW8U2ZSF89")

    def test_corrupted_check_digits_fail(self) -> None:
        """A single-digit corruption must be caught by the checksum."""
        assert not is_valid_lei("54930035WQZLGC45RZ36")

    def test_format_rejections(self) -> None:
        """Wrong length, case, check-digit letters, or empty values."""
        assert not is_lei_candidate(None)
        assert not is_lei_candidate("")
        assert not is_lei_candidate("54930035WQZLGC45RZ3")  # 19 chars
        assert not is_lei_candidate("54930035wqzlgc45rz35")  # lowercase
        assert not is_lei_candidate("TESTLEI00000000000AA")  # alpha check digits
        assert not is_valid_lei("TESTLEI00000000000AA")


class TestFindLeis:
    """Tests for LEI extraction from parsed messages."""

    def test_finds_unique_leis_with_source_tags(self) -> None:
        """The MAP swap ER carries two party LEIs (523) and the UTI
        generator's LEI (1905)."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)

        detected = find_leis(message)
        by_lei = {d.lei: d for d in detected}

        assert set(by_lei) == {
            "KNPC1X7GHDZW8U2ZSF89",
            "54930035WQZLGC45RZ35",
            "254900HSS82AHMTPAD95",
        }
        assert by_lei["KNPC1X7GHDZW8U2ZSF89"].source_tags == [523]
        assert by_lei["54930035WQZLGC45RZ35"].source_tags == [523]
        assert by_lei["254900HSS82AHMTPAD95"].source_tags == [1905]
        assert all(d.checksum_ok for d in detected)

    def test_ignores_non_lei_values(self) -> None:
        """Party values that are not LEI-shaped must not be reported."""
        message = FixMessage(
            fields=[
                FixField(tag=448, raw_value="BCQT"),
                FixField(tag=523, raw_value="(TEST) BANK ONE HK LTD"),
                FixField(tag=523, raw_value="29618590"),
                FixField(tag=58, raw_value="54930035WQZLGC45RZ35"),  # not LEI-bearing
            ]
        )
        assert find_leis(message) == []

    def test_dedupes_across_tags(self) -> None:
        """The same LEI seen in several tags yields one entry, all sources."""
        message = FixMessage(
            fields=[
                FixField(tag=523, raw_value="54930035WQZLGC45RZ35"),
                FixField(tag=1905, raw_value="54930035WQZLGC45RZ35"),
                FixField(tag=523, raw_value="54930035WQZLGC45RZ35"),
            ]
        )
        detected = find_leis(message)
        assert len(detected) == 1
        assert detected[0].source_tags == [523, 1905]

    def test_invalid_check_digits_still_detected(self) -> None:
        """LEI-shaped values with bad check digits are surfaced as invalid."""
        message = FixMessage(fields=[FixField(tag=523, raw_value="54930035WQZLGC45RZ36")])
        detected = find_leis(message)
        assert len(detected) == 1
        assert detected[0].checksum_ok is False


def _response(status_code: int, payload: object = None) -> object:
    class _FakeResponse:
        def __init__(self) -> None:
            self.status_code = status_code

        def json(self) -> object:
            if isinstance(payload, Exception):
                raise payload
            return payload

    return _FakeResponse()


class TestLookupLei:
    """Tests for the GLEIF lookup with the network mocked out."""

    LEI = "54930035WQZLGC45RZ35"

    def test_successful_lookup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = {
            "data": {
                "attributes": {
                    "lei": self.LEI,
                    "entity": {
                        "legalName": {"name": "ATF Test Bank 2"},
                        "status": "ACTIVE",
                        "jurisdiction": "GB",
                        "legalAddress": {"city": "London", "country": "GB"},
                    },
                    "registration": {"status": "ISSUED"},
                }
            }
        }
        monkeypatch.setattr(requests, "get", lambda url, timeout, headers: _response(200, payload))
        info = lookup_lei(self.LEI)
        assert info["legal_name"] == "ATF Test Bank 2"
        assert info["status"] == "ACTIVE"
        assert info["jurisdiction"] == "GB"
        assert info["city"] == "London"
        assert info["registration_status"] == "ISSUED"

    def test_not_found_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(requests, "get", lambda url, timeout, headers: _response(404))
        with pytest.raises(LeiLookupError, match="not found"):
            lookup_lei(self.LEI)

    def test_http_error_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(requests, "get", lambda url, timeout, headers: _response(503))
        with pytest.raises(LeiLookupError, match="HTTP 503"):
            lookup_lei(self.LEI)

    def test_network_failure_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _boom(url: str, timeout: float, headers: dict) -> object:
            raise requests.exceptions.ConnectionError("no route to host")

        monkeypatch.setattr(requests, "get", _boom)
        with pytest.raises(LeiLookupError, match="request failed"):
            lookup_lei(self.LEI)

    def test_malformed_payload_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            requests, "get", lambda url, timeout, headers: _response(200, {"data": {}})
        )
        with pytest.raises(LeiLookupError, match="payload"):
            lookup_lei(self.LEI)
