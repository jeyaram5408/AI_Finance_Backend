from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging


# -----------------------------------------------------------------------------------


def register_exception_handlers(app):

    # ---------------- HTTP Exceptions ----------------

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "errors": None,
            },
        )


    # ---------------- Request Validation ----------------

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Extract only the essential error information
        cleaned_errors = []

        for error in exc.errors():
            cleaned_errors.append({
                "loc": error.get("loc"),
                "msg": error.get("msg"),
                "type": error.get("type"),
            })

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Validation Error",
                "errors": cleaned_errors,
            },
        )
    

    # ---------------- Response Validation ----------------

    @app.exception_handler(ResponseValidationError)
    async def response_validation_handler(request: Request, exc: ResponseValidationError):
        logging.error(f"Response validation error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Response validation error",
                "errors": exc.errors(),
            },
        )


    # ---------------- Database Integrity ----------------

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logging.error(f"Integrity error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Database integrity error",
                "errors": None,
            },
        )


    # ---------------- General SQLAlchemy ----------------

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logging.error(f"Database error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Database error occurred",
                "errors": None,
            },
        )


    # ---------------- Permission Error ----------------

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        logging.error(f"Permission error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "message": "Permission denied",
                "errors": None,
            },
        )


    # ---------------- Value Error ----------------

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logging.error(f"Value error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(exc),
                "errors": None,
            },
        )

    # ---------------- Global Exception ----------------

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logging.error(f"Unexpected error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "errors": None,
            },
        )










# ------------------------- Extra Codes ----------------------------