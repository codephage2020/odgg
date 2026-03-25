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

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern in self.PATTERNS:
                record.msg = pattern.sub(r"\1***REDACTED***\2" if pattern.groups else r"\1***REDACTED***", record.msg)
        if record.args:
            new_args = []
            for arg in (record.args if isinstance(record.args, tuple) else (record.args,)):
                if isinstance(arg, str):
                    for pattern in self.PATTERNS:
                        arg = pattern.sub(r"\1***REDACTED***", arg)
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
