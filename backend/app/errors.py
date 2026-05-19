from dataclasses import dataclass
from typing import Optional


@dataclass
class AppError(Exception):
    error_code: str
    message: str
    action: Optional[str] = None
    retryable: bool = False

    def __post_init__(self) -> None:
        super().__init__(self.message)


@dataclass
class DuplicateDocumentError(AppError):
    existing_document_id: str = ""


def error_response(
    error_code: str,
    message: str,
    action: Optional[str] = None,
    retryable: bool = False,
) -> dict:
    return {
        "error_code": error_code,
        "message": message,
        "action": action,
        "retryable": retryable,
    }
