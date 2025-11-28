"""Middleware module for Legal Assistant."""

from .error_handler import ErrorHandlerMiddleware, setup_exception_handlers

__all__ = ["ErrorHandlerMiddleware", "setup_exception_handlers"]
