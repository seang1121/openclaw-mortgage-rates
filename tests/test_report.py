"""Unit tests for report formatting and rate parsing (openclaw-mortgage-rates)."""
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
)


class TestRateParsing:
    """Rate extraction from raw page text."""

    def test_30yr_rate_and_apr(self):
        text = "30-Year Fixed 6.875% some text APR 6.932%"
        results = extract_rates(text, "TestBank")
        assert len(results) >= 1
        assert results[0]["product"] == "30yr"
        assert results[0]["rate"] == 6.875
        assert results[0]["apr"] == 6.932

    def test_15yr_extraction(self):
        text = "15-Year Fixed 5.875% APR 5.950%"
        results = extract_rates(text, "TestBank")
        r15 = [r for r in results if r["product"] == "15yr"]
        assert len(r15) >= 1
        assert r15[0]["rate"] == 5.875

    def test_arm_extraction(self):
        text = "7/6 ARM 5.250% APR 5.400%"
        results = extract_rates(text, "TestBank")
        arm = [r for r in results if r["product"] == "ARM"]
        assert len(arm) >= 1

    def test_tab_separated_format(self):
        text = "30 Year\t6.500%\t6.600%"
        results = extract_rates(text, "TestBank")
        assert len(results) >= 1
        assert results[0]["rate"] == 6.500

    def test_is_format(self):
        text = "30-Year Fixed is 6.750% (6.810% APR)"
        results = extract_rates(text, "TestBank")
        assert results[0]["rate"] == 6.750
        assert results[0]["apr"] == 6.810

    def test_rate_only_no_apr(self):
        text = "30-Year Fixed 6.500%"
        results = extract_rates(text, "TestBank")
        assert results[0]["apr"] is None

    def test_empty_text_returns_empty(self):
        assert extract_rates("", "X") == []

    def test_garbage_text_returns_empty(self):
        assert extract_rates("buy groceries and fix the roof", "X") == []

    def test_multiple_products_parsed(self):
        text = (
            "30-Year Fixed 6.875% APR 6.932% "
            "15-Year Fixed 6.125% APR 6.200% "
            "5/1 ARM 5.500% APR 5.650%"
        )
        results = extract_rates(text, "TestBank")
        products = {r["product"] for r in results}
        assert products == {"30yr", "15yr", "ARM"}


class TestReportFormatting:
    """Discord-ready report output."""

    def _rates(self):
        return [
            {"lender": "Bank A", "product": "30yr", "rate": 6.500, "apr": 6.600},
            {"lender": "Bank B", "product": "30yr", "rate": 6.750, "apr": 6.800},
            {"lender": "Bank A", "product": "15yr", "rate": 5.875, "apr": 5.950},
            {"lender": "Freddie Mac (natl avg)", "product": "30yr", "rate": 6.650, "apr": None},
        ]

    def test_report_header_present(self):
        report = format_report(self._rates(), [])
        assert "MORTGAGE RATES" in report

    def test_report_lender_count(self):
        report = format_report(self._rates(), [])
        assert f"/{len(BROWSER_SOURCES)}" in report

    def test_product_sections_present(self):
        report = format_report(self._rates(), [])
        assert "30-YEAR FIXED" in report
        assert "15-YEAR FIXED" in report

    def test_best_rate_highlighted(self):
        report = format_report(self._rates(), [])
        lines = [l for l in report.split("\n") if "Bank A" in l and "30yr" not in l]
        # Bank A has the lowest 30yr rate, should be bold
        bank_a_30yr = [l for l in report.split("\n") if "Bank A" in l and "6.500" in l]
        assert any("**" in l for l in bank_a_30yr)

    def test_benchmark_marked(self):
        report = format_report(self._rates(), [])
        assert "benchmark" in report.lower()

    def test_apr_shown_when_available(self):
        report = format_report(self._rates(), [])
        assert "APR" in report

    def test_apr_omitted_when_none(self):
        rates = [{"lender": "Test", "product": "30yr", "rate": 6.5, "apr": None}]
        report = format_report(rates, [])
        test_line = [l for l in report.split("\n") if "Test" in l][0]
        assert "APR" not in test_line

    def test_empty_rates(self):
        report = format_report([], [])
        # Should still produce a header
        assert "MORTGAGE RATES" in report

    def test_day_over_day_down(self):
        rates = [{"lender": "Bank A", "product": "30yr", "rate": 6.0, "apr": 6.1}]
        history = [{"date": "2025-01-01", "rates": {
            "30yr": [{"lender": "Bank A", "rate": 7.0, "apr": 7.1}]
        }}]
        report = format_report(rates, history)
        assert "▼" in report

    def test_day_over_day_up(self):
        rates = [{"lender": "Bank A", "product": "30yr", "rate": 7.5, "apr": 7.6}]
        history = [{"date": "2025-01-01", "rates": {
            "30yr": [{"lender": "Bank A", "rate": 6.5, "apr": 6.6}]
        }}]
        report = format_report(rates, history)
        assert "▲" in report

    def test_day_over_day_unchanged(self):
        rates = [{"lender": "Bank A", "product": "30yr", "rate": 6.5, "apr": 6.6}]
        history = [{"date": "2025-01-01", "rates": {
            "30yr": [{"lender": "Bank A", "rate": 6.5, "apr": 6.6}]
        }}]
        report = format_report(rates, history)
        assert "unchanged" in report.lower()


class TestDiscordPostFormatting:
    """Report is valid for Discord consumption."""

    def test_no_code_blocks_unless_intended(self):
        rates = [{"lender": "Test", "product": "30yr", "rate": 6.5, "apr": 6.6}]
        report = format_report(rates, [])
        # Should not have accidental code blocks
        assert "```" not in report

    def test_report_length_reasonable(self):
        """Discord max message is 2000 chars; report should be under that."""
        rates = [
            {"lender": f"Bank {chr(65+i)}", "product": "30yr", "rate": 6.0 + i * 0.1, "apr": 6.1 + i * 0.1}
            for i in range(9)
        ]
        report = format_report(rates, [])
        assert len(report) < 2000, f"Report too long for Discord: {len(report)} chars"

    def test_bold_syntax_valid(self):
        rates = [{"lender": "Test", "product": "30yr", "rate": 6.5, "apr": 6.6}]
        report = format_report(rates, [])
        # Bold markers should come in pairs
        assert report.count("**") % 2 == 0

    def test_report_is_string(self):
        report = format_report([], [])
        assert isinstance(report, str)
