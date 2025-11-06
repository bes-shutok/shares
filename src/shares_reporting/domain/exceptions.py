"""
Custom exceptions for the shares reporting domain.

Provides specific exception types for different error scenarios
to enable better error handling and user-friendly messages.
"""


class SharesReportingError(Exception):
    """Base exception for all shares reporting errors."""
    pass


class FileProcessingError(SharesReportingError):
    """Raised when file processing fails."""
    pass


class DataValidationError(SharesReportingError):
    """Raised when data validation fails."""
    pass


class TradeProcessingError(SharesReportingError):
    """Raised when trade processing fails."""
    pass


class CapitalGainsCalculationError(SharesReportingError):
    """Raised when capital gains calculation fails."""
    pass


class ReportGenerationError(SharesReportingError):
    """Raised when report generation fails."""
    pass


class ConfigurationError(SharesReportingError):
    """Raised when configuration is invalid."""
    pass


class InsufficientDataError(SharesReportingError):
    """Raised when there's insufficient data for processing."""
    pass


class InvalidTradeDataError(DataValidationError):
    """Raised when trade data is invalid."""
    pass


class SecurityInfoExtractionError(DataValidationError):
    """Raised when security info extraction fails."""
    pass
