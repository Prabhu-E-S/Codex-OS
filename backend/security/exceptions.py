class SecurityScannerError(Exception):
    """Base exception for all security scanner errors."""
    pass

class ScannerUnavailableError(SecurityScannerError):
    """Raised when a requested security scanner is not installed or available."""
    pass

class ScannerExecutionError(SecurityScannerError):
    """Raised when a security scanner execution fails."""
    pass
