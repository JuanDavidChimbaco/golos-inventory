"""
Manejador global de excepciones DRF con formato consistente.
"""

from __future__ import annotations

from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    code = "ERROR"
    detail = "Ha ocurrido un error."
    errors: list[str] = []

    if isinstance(data, list):
        errors = [str(item) for item in data]
        if errors:
            detail = errors[0]
    elif isinstance(data, dict):
        if "detail" in data:
            if isinstance(data["detail"], list):
                errors = [str(item) for item in data["detail"]]
                detail = errors[0] if errors else detail
            else:
                detail = str(data["detail"])
                errors = [detail]
            if hasattr(exc, "default_code"):
                code = str(exc.default_code).upper()
        else:
            for field, value in data.items():
                if isinstance(value, list):
                    errors.extend([f"{field}: {item}" for item in value])
                else:
                    errors.append(f"{field}: {value}")
            if errors:
                detail = errors[0]
            code = "VALIDATION_ERROR"
    else:
        detail = str(data)
        errors = [detail]

    response.data = {
        "detail": detail,
        "code": code,
        "errors": errors or [detail],
    }
    return response
