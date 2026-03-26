"""Tests for credential redaction in logging."""

import logging

from odgg.core.logging import CredentialRedactFilter, setup_logging


class TestCredentialRedactFilter:
    def setup_method(self):
        self.filter = CredentialRedactFilter()

    def _make_record(self, msg: str, args=None) -> logging.LogRecord:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=args, exc_info=None,
        )
        return record

    def test_redacts_url_password(self):
        record = self._make_record("connecting to postgresql://user:secretpass@localhost/db")
        self.filter.filter(record)
        assert "secretpass" not in record.msg
        assert "***REDACTED***" in record.msg
        assert "postgresql://" in record.msg

    def test_redacts_password_field(self):
        record = self._make_record("config: password=my_secret_123")
        self.filter.filter(record)
        assert "my_secret_123" not in record.msg
        assert "***REDACTED***" in record.msg

    def test_redacts_api_key(self):
        record = self._make_record("using api_key=sk-1234567890abcdef")
        self.filter.filter(record)
        assert "sk-1234567890abcdef" not in record.msg
        assert "***REDACTED***" in record.msg

    def test_preserves_safe_messages(self):
        record = self._make_record("discovered 5 tables in schema public")
        self.filter.filter(record)
        assert record.msg == "discovered 5 tables in schema public"

    def test_redacts_in_args(self):
        record = self._make_record("connect: %s", ("postgresql://u:pass@host",))
        self.filter.filter(record)
        assert "pass" not in str(record.args)
        assert "***REDACTED***" in str(record.args)

    def test_returns_true(self):
        record = self._make_record("test")
        assert self.filter.filter(record) is True

    def test_redacts_password_with_colon(self):
        record = self._make_record("password: hunter2")
        self.filter.filter(record)
        assert "hunter2" not in record.msg

    def test_redacts_api_key_with_hyphen(self):
        record = self._make_record("api-key = sk-abc123")
        self.filter.filter(record)
        assert "sk-abc123" not in record.msg


class TestSetupLogging:
    def test_setup_info_level(self):
        setup_logging(debug=False)
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_setup_debug_level(self):
        setup_logging(debug=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_handler_has_redact_filter(self):
        setup_logging()
        root = logging.getLogger()
        assert len(root.handlers) == 1
        filters = root.handlers[0].filters
        assert any(isinstance(f, CredentialRedactFilter) for f in filters)
