"""Domain-specific exceptions."""


class AutomationError(RuntimeError):
    """Base exception for automation failures."""


class ConfigurationError(AutomationError):
    """Raised when local configuration is invalid."""


class ChromeNotFoundError(AutomationError):
    """Raised when Google Chrome cannot be located."""


class ChromeConnectionError(AutomationError):
    """Raised when the Chrome DevTools endpoint is unavailable."""


class GCPJPageNotFoundError(AutomationError):
    """Raised when no authenticated GCPJ page is found."""


class GCPJNotAuthenticatedError(AutomationError):
    """Raised when the GCPJ session is not authenticated."""


class SelectorNotFoundError(AutomationError):
    """Raised when a required GCPJ element cannot be located."""


class ProcessNotFoundError(AutomationError):
    """Raised when the supplied NPC is not found in GCPJ."""


class ReasonMappingError(AutomationError):
    """Raised when an Excel ATO cannot be mapped to a GCPJ reason."""


class ReasonNotAvailableError(AutomationError):
    """Raised when the mapped reason is not available in the GCPJ dropdown."""


class SpreadsheetValidationError(AutomationError):
    """Raised when the uploaded spreadsheet is invalid."""
