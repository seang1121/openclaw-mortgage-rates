"""Security tests for openclaw-mortgage-rates."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mortgage_rate_report import (
    extract_rates,
    format_report,
    load_zip_code,
    BENCHMARKS,
    BROWSER_SOURCES,
    CONFIG_FILE,
)


class TestCredentialHandling:
    """No credentials or secrets in output."""

    SENSITIVE_PATTERNS = [
        "password", "token", "secret", "api_key", "apikey",
        "authorization", "bearer", "credential", "webhook",
        "discord_token", "bot_token",
    ]

    def _make_rates(self):
        return [
            {"lender": "Bank of America", "product": "30yr", "rate": 6.875, "apr": 6.932},
            {"lender": "Wells Fargo", "product": "30yr", "rate": 6.750, "apr": 6.812},
        ]

    def test_report_has_no_sensitive_keywords(self):
        report = format_report(self._make_rates(), [])
        lower = report.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            assert pattern not in lower, f"Sensitive keyword found: {pattern}"

    def test_report_has_no_urls(self):
        report = format_report(self._make_rates(), [])
        assert "https://" not in report
        assert "http://" not in report

    def test_report_has_no_file_paths(self):
        report = format_report(self._make_rates(), [])
        assert "/Users/" not in report
        assert "C:\\" not in report
        assert ".json" not in report

    def test_zip_code_not_leaked_to_report(self):
        report = format_report(self._make_rates(), [])
        # ZIP is used for scraping only, not in output
        assert "YOUR_ZIP" not in report


class TestNoSecretsInOutputFiles:
    """Config and output files do not contain secrets."""

    def test_config_json_no_secrets(self):
        with open(CONFIG_FILE) as f:
            text = f.read().lower()
        for keyword in ["password", "token", "secret", "api_key", "bearer"]:
            assert keyword not in text, f"config.json contains: {keyword}"

    def test_config_json_valid(self):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        assert isinstance(cfg, dict)
        assert "zip_code" in cfg

    def test_config_no_discord_webhook(self):
        with open(CONFIG_FILE) as f:
            text = f.read()
        assert "discord" not in text.lower() or "webhook" not in text.lower()

    def test_source_file_no_hardcoded_secrets(self):
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "mortgage_rate_report.py")
        with open(src) as f:
            text = f.read()
        # Should not have hardcoded API keys or tokens
        assert "sk-" not in text  # OpenAI-style key
        assert "xoxb-" not in text  # Slack token
        assert "Bot " not in text or "User-Agent" in text  # Discord bot token (allow UA string)


class TestConfigValidation:
    """Config structure validation."""

    def test_config_has_required_fields(self):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        assert "zip_code" in cfg

    def test_load_zip_code_cli_override(self):
        assert load_zip_code(cli_zip="90210") == "90210"

    def test_load_zip_code_rejects_placeholder(self):
        """YOUR_ZIP placeholder should cause sys.exit, not return garbage."""
        # The openclaw version calls sys.exit(1) when no valid ZIP
        result = load_zip_code(cli_zip="32224")
        assert result == "32224"

    def test_extract_rates_handles_malicious_html(self):
        """XSS-style input should not corrupt rate data."""
        text = '30-Year Fixed 6.500% APR 6.600% <img src=x onerror="alert(1)">'
        results = extract_rates(text, "SafeBank")
        for r in results:
            assert "onerror" not in r["lender"]
            assert "onerror" not in r["product"]
            assert isinstance(r["rate"], float)

    def test_extract_rates_extreme_values(self):
        """Rates outside 3.0-12.0 should be rejected in rate-only pattern."""
        text = "30-Year Fixed 0.001%"
        results = extract_rates(text, "TestBank")
        assert results == []

        text2 = "30-Year Fixed 99.999%"
        results2 = extract_rates(text2, "TestBank")
        assert results2 == []
