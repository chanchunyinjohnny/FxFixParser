"""Custom exceptions for FIX message parsing."""


class ParseError(Exception):
    """Raised when a FIX message cannot be parsed."""

    def __init__(self, message: str, position: int | None = None) -> None:
        self.position = position
        if position is not None:
            message = f"{message} at position {position}"
        super().__init__(message)


class ChecksumError(ParseError):
    """Raised when FIX message checksum validation fails."""

    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"Checksum mismatch: expected {expected}, got {actual}")


class ValidationError(ParseError):
    """Raised when FIX message structure validation fails."""

    def __init__(self, message: str, tag: int | None = None) -> None:
        self.tag = tag
        if tag is not None:
            message = f"{message} (tag {tag})"
        super().__init__(message)
