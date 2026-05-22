"""Custom exceptions for debate SDK shared infrastructure."""


class BudgetExceededException(Exception):  # noqa: N818
    """Raised when projected token usage exceeds the configured budget."""
