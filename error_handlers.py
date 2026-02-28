"""
Standardized error handling and response schemas for Litterboxd API.
Ensures consistent error responses across all endpoints.
"""

from pydantic import BaseModel
from typing import Optional, Any, Dict
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Standard error response detail"""
    code: str
    message: str
    field: Optional[str] = None
    constraint: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: ErrorDetail
    status_code: int
    request_id: Optional[str] = None
    timestamp: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response schema for list endpoints"""
    data: Any
    count: Optional[int] = None
    status_code: int = 200


# ============= VALIDATION ERROR CODES =============

class ValidationError(HTTPException):
    """Validation error - 400 Bad Request"""
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        constraint: Optional[str] = None,
        code: str = "VALIDATION_ERROR"
    ):
        self.error_detail = ErrorDetail(
            code=code,
            message=message,
            field=field,
            constraint=constraint
        )
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=self.error_detail.model_dump()
        )


class NotFoundError(HTTPException):
    """Resource not found - 404 Not Found"""
    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        code: str = "NOT_FOUND"
    ):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        
        self.error_detail = ErrorDetail(
            code=code,
            message=message
        )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=self.error_detail.model_dump()
        )


class ConflictError(HTTPException):
    """Resource conflict - 409 Conflict"""
    def __init__(
        self,
        message: str,
        code: str = "CONFLICT"
    ):
        self.error_detail = ErrorDetail(
            code=code,
            message=message
        )
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=self.error_detail.model_dump()
        )


class UnauthorizedError(HTTPException):
    """Unauthorized - 401"""
    def __init__(
        self,
        message: str = "Unauthorized",
        code: str = "UNAUTHORIZED"
    ):
        self.error_detail = ErrorDetail(
            code=code,
            message=message
        )
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=self.error_detail.model_dump()
        )


class ForbiddenError(HTTPException):
    """Forbidden - 403"""
    def __init__(
        self,
        message: str,
        code: str = "FORBIDDEN"
    ):
        self.error_detail = ErrorDetail(
            code=code,
            message=message
        )
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=self.error_detail.model_dump()
        )


class InternalServerError(HTTPException):
    """Internal server error - 500"""
    def __init__(
        self,
        message: str = "Internal server error",
        code: str = "INTERNAL_SERVER_ERROR"
    ):
        self.error_detail = ErrorDetail(
            code=code,
            message=message
        )
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=self.error_detail.model_dump()
        )


# ============= VALIDATION HELPERS =============

def validate_rating(rating: int, field_name: str = "rating") -> None:
    """Validate rating is between 1 and 10"""
    if rating < 1 or rating > 10:
        raise ValidationError(
            message=f"{field_name} must be between 1 and 10",
            field=field_name,
            constraint="range",
            code="INVALID_RATING"
        )


def validate_string_not_empty(value: str, field_name: str) -> None:
    """Validate string is not empty"""
    if not value or not value.strip():
        raise ValidationError(
            message=f"{field_name} cannot be empty",
            field=field_name,
            constraint="not_empty",
            code="EMPTY_STRING"
        )


def validate_floor_number(floor: int) -> None:
    """Validate floor number is positive"""
    if floor < 0:
        raise ValidationError(
            message="Floor number must be non-negative",
            field="floor_number",
            constraint="non_negative",
            code="INVALID_FLOOR"
        )


def validate_url(url: str) -> None:
    """Basic URL validation"""
    if not url.startswith(("http://", "https://")):
        raise ValidationError(
            message="URL must start with http:// or https://",
            field="url",
            constraint="valid_url",
            code="INVALID_URL"
        )


def validate_bathroom_id(bathroom_id: int) -> None:
    """Validate bathroom_id is positive"""
    if bathroom_id <= 0:
        raise ValidationError(
            message="Bathroom ID must be positive",
            field="bathroom_id",
            constraint="positive",
            code="INVALID_ID"
        )


def validate_stall_number(stall_number: int) -> None:
    """Validate stall number is positive"""
    if stall_number <= 0:
        raise ValidationError(
            message="Stall number must be positive",
            field="stall_number",
            constraint="positive",
            code="INVALID_STALL"
        )
