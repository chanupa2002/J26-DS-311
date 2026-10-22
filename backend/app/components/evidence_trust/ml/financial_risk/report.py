"""Report serialization helpers."""

from .contracts import FinancialReport


def report_dict(report: FinancialReport) -> dict:
    """Serialize a financial report to JSON-safe data."""
    return report.as_dict()


def readable_report(report: FinancialReport) -> str:
    """Serialize a financial report to readable text."""
    return report.as_text()
