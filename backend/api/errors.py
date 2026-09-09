from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class OceanAPIError(Exception):
    status_code = 500
    code = "OCEAN_API_ERROR"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)

        self.message = message

        if status_code is not None:
            self.status_code = status_code

        if code is not None:
            self.code = code

class OceanEmbedAPIError(Exception):
    """Base exception for OceanEmbed API errors."""


class DataNotAvailableError(OceanEmbedAPIError):
    """Requested data does not exist for the requested coordinates/date/depth."""


class InvalidCoordinateError(OceanEmbedAPIError):
    """Requested geographic coordinate is invalid or outside the model domain."""


class InvalidDateError(OceanEmbedAPIError):
    """Requested date is invalid or outside the available analysis period."""


class InvalidDepthError(OceanEmbedAPIError):
    """Requested depth is not available in the model."""


class InvalidVariableError(OceanEmbedAPIError):
    """Requested field variable is not supported."""


class LandCellError(OceanEmbedAPIError):
    """Requested coordinate falls on land rather than an ocean model cell."""

class InvalidCoordinateError(OceanAPIError):
    status_code = 400
    code = "INVALID_COORDINATE"


class InvalidDateError(OceanAPIError):
    status_code = 400
    code = "INVALID_DATE"


class DateUnavailableError(OceanAPIError):
    status_code = 404
    code = "DATE_UNAVAILABLE"


class VariableNotFoundError(OceanAPIError):
    status_code = 404
    code = "VARIABLE_NOT_FOUND"


class DepthUnavailableError(OceanAPIError):
    status_code = 400
    code = "DEPTH_UNAVAILABLE"


class DatasetUnavailableError(OceanAPIError):
    status_code = 503
    code = "DATASET_UNAVAILABLE"


class GridCellNotFoundError(OceanAPIError):
    status_code = 404
    code = "GRID_CELL_NOT_FOUND"


async def ocean_api_exception_handler(
    request: Request,
    exc: OceanAPIError,
) -> JSONResponse:

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
            }
        },
    )