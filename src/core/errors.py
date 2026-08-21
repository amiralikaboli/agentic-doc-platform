from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse


class DomainException(Exception):
    def __init__(
            self,
            message: str,
            status_code: int = status.HTTP_400_BAD_REQUEST,
            error_code: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ResourceNotFound(DomainException):
    def __init__(self, resource: str, identifier: str, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found: {identifier}"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "identifier": identifier, **(details or {})},
        )


class ValidationError(DomainException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class ExternalServiceError(DomainException):
    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_message = f"{service} error: {message}"
        super().__init__(
            message=full_message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})},
        )


class InternalServerError(DomainException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            details=details,
        )


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
