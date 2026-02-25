"""
Helpers para respuestas API consistentes.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response


def build_success_payload(detail: str, code: str = "SUCCESS", **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"detail": detail, "code": code}
    payload.update(extra)
    return payload


def build_error_payload(
    detail: str,
    code: str = "ERROR",
    errors: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    normalized_errors = errors or [detail]
    payload: dict[str, Any] = {"detail": detail, "code": code, "errors": normalized_errors}
    payload.update(extra)
    return payload


def validation_error_payload(
    exc: Exception,
    default_detail: str = "Error de validacion",
    default_code: str = "VALIDATION_ERROR",
) -> dict[str, Any]:
    errors: list[str] = []

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            for field, messages in exc.message_dict.items():
                if isinstance(messages, (list, tuple)):
                    errors.extend([f"{field}: {message}" for message in messages])
                else:
                    errors.append(f"{field}: {messages}")
        elif hasattr(exc, "messages"):
            errors.extend([str(message) for message in exc.messages])
        else:
            errors.append(str(exc))
    else:
        errors.append(str(exc))

    normalized_errors = [error for error in errors if error]
    detail = normalized_errors[0] if normalized_errors else default_detail
    return build_error_payload(detail=detail, code=default_code, errors=normalized_errors or [default_detail])


def success_response(
    detail: str,
    code: str = "SUCCESS",
    http_status: int = status.HTTP_200_OK,
    **extra: Any,
) -> Response:
    return Response(build_success_payload(detail=detail, code=code, **extra), status=http_status)


def error_response(
    detail: str,
    code: str = "ERROR",
    http_status: int = status.HTTP_400_BAD_REQUEST,
    errors: list[str] | None = None,
    **extra: Any,
) -> Response:
    return Response(
        build_error_payload(detail=detail, code=code, errors=errors, **extra),
        status=http_status,
    )
