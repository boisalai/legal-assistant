"""
Middleware de gestion d'erreurs pour FastAPI.

Capture toutes les exceptions et retourne des réponses JSON structurées.
"""

import logging
import traceback
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from exceptions import NotaryException


logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui capture toutes les exceptions et retourne des réponses JSON structurées.

    Avantages:
    - Format d'erreur cohérent pour toute l'API
    - Logs détaillés des erreurs
    - Pas de stack traces exposés aux clients
    - Codes HTTP appropriés selon le type d'erreur
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Traite la requête et capture les exceptions.

        Args:
            request: Requête HTTP
            call_next: Fonction pour exécuter le handler suivant

        Returns:
            Response HTTP
        """
        try:
            response = await call_next(request)
            return response

        except NotaryException as e:
            # Exceptions métier personnalisées
            logger.warning(
                f"Business exception: {e.message}",
                extra={
                    "status_code": e.status_code,
                    "details": e.details,
                    "path": request.url.path,
                    "method": request.method,
                }
            )

            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "message": e.message,
                        "type": type(e).__name__,
                        "details": e.details,
                    }
                },
            )

        except ValueError as e:
            # Erreurs de validation Python standard
            logger.warning(
                f"Validation error: {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                }
            )

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": {
                        "message": str(e),
                        "type": "ValidationError",
                    }
                },
            )

        except Exception as e:
            # Toutes les autres exceptions (erreurs inattendues)
            logger.error(
                f"Unexpected error: {str(e)}",
                exc_info=True,
                extra={
                    "path": request.url.path,
                    "method": request.method,
                }
            )

            # En production, ne pas exposer les détails de l'erreur
            # En développement, inclure le traceback
            error_detail = {
                "error": {
                    "message": "An unexpected error occurred",
                    "type": "InternalServerError",
                }
            }

            # Ajouter le traceback en mode debug
            import os
            if os.getenv("DEBUG", "false").lower() == "true":
                error_detail["error"]["traceback"] = traceback.format_exc()

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_detail,
            )


def setup_exception_handlers(app):
    """
    Configure les handlers d'exception globaux pour FastAPI.

    Args:
        app: Instance FastAPI
    """
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(NotaryException)
    async def notary_exception_handler(request: Request, exc: NotaryException):
        """Handler pour les exceptions métier personnalisées."""
        logger.warning(
            f"Business exception: {exc.message}",
            extra={
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "type": type(exc).__name__,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handler pour les erreurs de validation Pydantic."""
        logger.warning(
            f"Validation error: {exc.errors()}",
            extra={
                "path": request.url.path,
                "errors": exc.errors(),
            }
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "message": "Validation failed",
                    "type": "ValidationError",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handler pour les HTTPException de Starlette."""
        logger.info(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={
                "path": request.url.path,
                "status_code": exc.status_code,
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.detail,
                    "type": "HTTPException",
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handler pour toutes les autres exceptions."""
        logger.error(
            f"Unexpected error: {str(exc)}",
            exc_info=True,
            extra={
                "path": request.url.path,
            }
        )

        error_detail = {
            "error": {
                "message": "An unexpected error occurred",
                "type": "InternalServerError",
            }
        }

        # Ajouter le traceback en mode debug
        import os
        if os.getenv("DEBUG", "false").lower() == "true":
            error_detail["error"]["traceback"] = traceback.format_exc()

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_detail,
        )
