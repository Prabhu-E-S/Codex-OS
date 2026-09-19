import re
from typing import Optional
from backend.evaluation.models import EvidenceItem, EvidenceSourceType

SECRET_PATTERNS = [
    # Explicit secret token prefixes (e.g. sk-..., ghp_...)
    (
        re.compile(r"""(?i)\b(sk-[a-zA-Z0-9_\-]{6,})\b"""),
        "<REDACTED>"
    ),
    (
        re.compile(r"""(?i)\b(ghp_[a-zA-Z0-9]{10,})\b"""),
        "<REDACTED>"
    ),
    # Key-value secret patterns (API keys, secrets, passwords, tokens)
    (
        re.compile(r"""(?i)\b(api[_-]?key|secret[_-]?key|client[_-]?secret|password|auth[_-]?token|bearer[_-]?token|token|access[_-]?key|private[_-]?key)\b\s*[:=]\s*['"]?([^\s'"]{4,})['"]?"""),
        r'\1="<REDACTED>"'
    ),
    # AWS Access Key IDs
    (
        re.compile(r"""AKIA[0-9A-Z]{16}"""),
        "AKIA<REDACTED>"
    ),
    # Private Key blocks
    (
        re.compile(r"""-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"""),
        "-----BEGIN PRIVATE KEY-----\n<REDACTED>\n-----END PRIVATE KEY-----"
    ),
]

def redact_sensitive_text(text: Optional[str]) -> Optional[str]:
    """
    Redact secrets, tokens, API keys, passwords, and private keys from evidence text.
    Ensures stored evidence never exposes sensitive repository or runtime credentials.
    """
    if not text:
        return text

    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def make_evidence_item(
    dimension: str,
    source_type: EvidenceSourceType | str,
    metric_name: str,
    metric_value: Optional[str],
    description: str,
    unit: Optional[str] = None,
    evidence_text: Optional[str] = None,
    file_path: Optional[str] = None,
    line_number: Optional[int] = None,
    source_id: Optional[str] = None,
) -> EvidenceItem:
    """
    Construct a validated EvidenceItem with automatic secret redaction on evidence_text.
    """
    st_val = source_type.value if hasattr(source_type, "value") else str(source_type)
    return EvidenceItem(
        dimension=dimension,
        source_type=st_val,
        metric_name=metric_name,
        metric_value=str(metric_value) if metric_value is not None else None,
        unit=unit,
        description=description,
        evidence_text=redact_sensitive_text(evidence_text),
        file_path=file_path,
        line_number=line_number,
        source_id=source_id,
    )
