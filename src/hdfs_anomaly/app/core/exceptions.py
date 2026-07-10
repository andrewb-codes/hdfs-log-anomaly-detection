class AppError(Exception):
    status_code = 500
    detail = "error.internal"


class DuplicateEmailError(AppError):
    status_code = 409
    detail = "error.email.already_exists"


class InvalidCredentialsError(AppError):
    status_code = 401
    detail = "error.auth.invalid_credentials"


class ProfileVersionConflictError(AppError):
    status_code = 409
    detail = "error.profile.version_conflict"


class InvalidCurrentPasswordError(AppError):
    status_code = 400
    detail = "error.password.invalid_current"


class SameEmailError(AppError):
    status_code = 400
    detail = "error.email.same_as_current"


class SamePasswordError(AppError):
    status_code = 400
    detail = "error.password.same_as_current"


class UnauthorizedError(AppError):
    status_code = 401
    detail = "error.auth.unauthorized"


class SelfLikeError(AppError):
    status_code = 400
    detail = "error.charm.self_like"


class ForbiddenError(AppError):
    status_code = 403
    detail = "error.auth.forbidden"


class ProfileNotFoundError(AppError):
    status_code = 404
    detail = "error.profile.not_found"


class AdminSelfModificationError(AppError):
    status_code = 400
    detail = "error.admin.self_modification"
