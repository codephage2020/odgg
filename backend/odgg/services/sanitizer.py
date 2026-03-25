"""Input sanitizer for prompt injection defense and SQL identifier safety."""

from __future__ import annotations

import re


# Characters allowed in SQL identifiers (conservative allowlist)
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Patterns that indicate prompt injection attempts in metadata values
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|above|all)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+(now|a)\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(system|prompt|instruction)", re.IGNORECASE),
    re.compile(r"\b(DROP|DELETE|TRUNCATE|ALTER)\s+(TABLE|DATABASE)\b", re.IGNORECASE),
]


def sanitize_identifier(name: str) -> str:
    """Sanitize a database identifier for safe use in prompts and SQL.

    Strips non-alphanumeric characters (except underscore) and validates format.
    Returns the sanitized name or raises ValueError for completely invalid input.
    """
    if not name or not name.strip():
        raise ValueError("Identifier cannot be empty")

    # Strip leading/trailing whitespace
    cleaned = name.strip()

    # Replace common separator characters with underscores
    cleaned = re.sub(r"[\s\-\.]+", "_", cleaned)

    # Remove any remaining non-alphanumeric/underscore characters
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", cleaned)

    # Ensure it starts with a letter or underscore
    if cleaned and cleaned[0].isdigit():
        cleaned = f"_{cleaned}"

    if not cleaned:
        raise ValueError(f"Identifier '{name}' contains no valid characters")

    return cleaned


def is_safe_identifier(name: str) -> bool:
    """Check if a string is a safe SQL identifier without modification."""
    return bool(_IDENTIFIER_RE.match(name))


def detect_prompt_injection(text: str) -> bool:
    """Check if text contains known prompt injection patterns."""
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


def sanitize_for_prompt(value: str, max_length: int = 200) -> str:
    """Sanitize a metadata value for inclusion in an LLM prompt.

    Truncates, strips control characters, and checks for injection attempts.
    """
    if not value:
        return ""

    # Remove control characters except newlines and tabs
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)

    # Truncate to prevent context stuffing
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."

    return cleaned


def quote_identifier(name: str) -> str:
    """Return a safely quoted SQL identifier using double quotes.

    This is the PostgreSQL standard for delimited identifiers.
    """
    sanitized = sanitize_identifier(name)
    # Double any internal quotes
    escaped = sanitized.replace('"', '""')
    return f'"{escaped}"'
