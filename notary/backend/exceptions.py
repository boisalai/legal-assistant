"""
Exceptions personnalisées pour Notary Assistant.

Classes d'exception pour différents types d'erreurs métier.
"""


class NotaryException(Exception):
    """Exception de base pour toutes les exceptions métier."""

    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ResourceNotFoundError(NotaryException):
    """Ressource introuvable."""

    def __init__(self, resource_type: str, resource_id: str, details: dict = None):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(message, status_code=404, details=details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ValidationError(NotaryException):
    """Erreur de validation des données."""

    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(message, status_code=422, details=details)
        self.field = field


class DatabaseError(NotaryException):
    """Erreur de base de données."""

    def __init__(self, message: str, operation: str = None, details: dict = None):
        super().__init__(message, status_code=500, details=details)
        self.operation = operation


class FileUploadError(NotaryException):
    """Erreur lors de l'upload de fichier."""

    def __init__(self, message: str, filename: str = None, details: dict = None):
        super().__init__(message, status_code=400, details=details)
        self.filename = filename


class WorkflowError(NotaryException):
    """Erreur lors de l'exécution d'un workflow."""

    def __init__(self, message: str, workflow_name: str = None, step: str = None, details: dict = None):
        super().__init__(message, status_code=500, details=details)
        self.workflow_name = workflow_name
        self.step = step


class ExternalServiceError(NotaryException):
    """Erreur lors de l'appel à un service externe (LLM, etc.)."""

    def __init__(self, message: str, service_name: str = None, details: dict = None):
        super().__init__(message, status_code=503, details=details)
        self.service_name = service_name


class AuthenticationError(NotaryException):
    """Erreur d'authentification."""

    def __init__(self, message: str = "Authentication required", details: dict = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(NotaryException):
    """Erreur d'autorisation."""

    def __init__(self, message: str = "Not authorized to access this resource", details: dict = None):
        super().__init__(message, status_code=403, details=details)
