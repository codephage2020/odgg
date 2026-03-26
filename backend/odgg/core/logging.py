"""Logging configuration with credential redaction."""

import logging
import re


class CredentialRedactFilter(logging.Filter):
    """Filter that redacts passwords and credentials from log output."""

    # Matches common patterns: postgresql://user:PASSWORD@host, password=SECRET
    PATTERNS = [
        re.compile(r"(://[^:]+:)[^@]+(@)", re.IGNORECASE),
        re.compile(r"(password\s*[=:]\s*)\S+", re.IGNORECASE),
        re.compile(r"(api[_-]?key\s*[=:]\s*)\S+", re.IGNORECASE),
    ]

    # Replacement strings per pattern (must match group count)
    REPLACEMENTS = [
        r"\1***REDACTED***\2",  # URL pattern has 2 groups
        r"\1***REDACTED***",    # password pattern has 1 group
        r"\1***REDACTED***",    # api_key pattern has 1 group
    ]

    def _redact(self, text: str) -> str:
        for pattern, repl in zip(self.PATTERNS, self.REPLACEMENTS):
            text = pattern.sub(repl, text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if record.args:
            new_args = []
            for arg in (record.args if isinstance(record.args, tuple) else (record.args,)):
                if isinstance(arg, str):
                    arg = self._redact(arg)
                new_args.append(arg)
            record.args = tuple(new_args) if isinstance(record.args, tuple) else new_args[0]
        return True


def setup_logging(debug: bool = False) -> None:
    """Configure application logging with credential redaction."""
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler()
    handler.addFilter(CredentialRedactFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
