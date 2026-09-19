class EvaluationError(Exception):
    """Base exception for the evaluation subsystem."""
    pass

class InvalidScoreWeightsError(EvaluationError):
    """Raised when score configuration weights do not sum to 1.0 or are invalid."""
    pass

class InsufficientEvidenceError(EvaluationError):
    """Raised when an evaluation cannot be performed due to complete absence of evidence."""
    pass

class EvaluationNotFoundError(EvaluationError):
    """Raised when a requested evaluation record does not exist."""
    pass
