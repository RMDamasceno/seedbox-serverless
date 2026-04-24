"""Exceções customizadas da API."""


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class BadRequestError(ApiError):
    def __init__(self, message: str = "bad_request"):
        super().__init__(message, 400)


class UnauthorizedError(ApiError):
    def __init__(self, message: str = "unauthorized"):
        super().__init__(message, 401)


class NotFoundError(ApiError):
    def __init__(self, message: str = "not_found"):
        super().__init__(message, 404)


class ConflictError(ApiError):
    def __init__(self, message: str = "conflict"):
        super().__init__(message, 409)
