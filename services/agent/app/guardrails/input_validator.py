"""Input-level validation: file size, MIME type, and content sanity."""
from dataclasses import dataclass


MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024
MAX_TEXT_LENGTH = 50_000
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_PREFIXES = (b"\x89PNG", b"\xff\xd8\xff", b"GIF8")
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/gif"}
ALLOWED_LOG_MIME_TYPES = {
    "text/plain",
    "text/x-log",
    "application/log",
    "application/x-log",
    "application/json",
    "application/x-ndjson",
}
DISALLOWED_LOG_MIME_TYPES = {
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/x-msdownload",
    "application/octet-stream+binary",
}
DISALLOWED_LOG_MIME_PREFIXES = ("image/", "audio/", "video/")
PRINTABLE_TEXT_THRESHOLD = 0.85


@dataclass
class ValidationResult:
    ok: bool
    reason: str | None = None


def validate_text(text: str) -> ValidationResult:
    if not text or not text.strip():
        return ValidationResult(False, "Empty text input")
    if len(text) > MAX_TEXT_LENGTH:
        return ValidationResult(False, f"Text too long ({len(text)} > {MAX_TEXT_LENGTH})")
    return ValidationResult(True)


def validate_log_content(content: str) -> ValidationResult:
    if len(content.encode("utf-8")) > MAX_LOG_SIZE_BYTES:
        return ValidationResult(False, f"Log file exceeds {MAX_LOG_SIZE_BYTES} bytes")
    if not content.strip():
        return ValidationResult(False, "Log file is empty")
    if content.count("\n") < 2:
        return ValidationResult(False, "Log file has no recognizable structure")
    return ValidationResult(True)


def validate_log_upload(
    content_bytes: bytes | None,
    content_type: str | None = None,
) -> ValidationResult:
    if content_bytes is None:
        return ValidationResult(False, "Log file is missing")
    if len(content_bytes) > MAX_LOG_SIZE_BYTES:
        return ValidationResult(False, f"Log file exceeds {MAX_LOG_SIZE_BYTES} bytes")

    normalized_type = _normalize_content_type(content_type)
    if normalized_type:
        if normalized_type in DISALLOWED_LOG_MIME_TYPES or normalized_type.startswith(
            DISALLOWED_LOG_MIME_PREFIXES
        ):
            return ValidationResult(False, f"Log MIME type is not allowed ({normalized_type})")
        if (
            normalized_type not in ALLOWED_LOG_MIME_TYPES
            and normalized_type != "application/octet-stream"
            and not normalized_type.startswith("text/")
        ):
            return ValidationResult(False, f"Unexpected log MIME type ({normalized_type})")

    if _looks_binary(content_bytes):
        return ValidationResult(False, "Log file appears to contain suspicious binary content")

    try:
        decoded = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return ValidationResult(False, "Log file is not valid UTF-8 text")

    return validate_log_content(decoded)


def validate_image_bytes(
    image_bytes: bytes | None,
    content_type: str | None = None,
) -> ValidationResult:
    if image_bytes is None:
        return ValidationResult(True)
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        return ValidationResult(False, f"Image exceeds {MAX_IMAGE_SIZE_BYTES} bytes")

    normalized_type = _normalize_content_type(content_type)
    if normalized_type and normalized_type not in ALLOWED_IMAGE_MIME_TYPES:
        return ValidationResult(
            False,
            f"Image MIME type is not allowed ({normalized_type})",
        )

    if not any(image_bytes.startswith(prefix) for prefix in ALLOWED_IMAGE_PREFIXES):
        return ValidationResult(
            False,
            "Image format not recognized (only PNG, JPEG, GIF allowed)",
        )
    return ValidationResult(True)


def _normalize_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _looks_binary(content_bytes: bytes) -> bool:
    if not content_bytes:
        return False

    sample = content_bytes[:4096]
    if b"\x00" in sample:
        return True

    printable = sum(1 for b in sample if b in (9, 10, 13) or 32 <= b <= 126)
    return (printable / len(sample)) < PRINTABLE_TEXT_THRESHOLD

