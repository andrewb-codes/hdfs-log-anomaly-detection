from enum import StrEnum


class RateLimitScope(StrEnum):
    LOGIN_ACCOUNT = "login_account"
    LOGIN_GLOBAL = "login_global"
    REGISTER_IDENTIFIER = "register_identifier"
    REGISTER_GLOBAL = "register_global"
    PROFILE_READ = "profile_read"
    PROFILE_WRITE = "profile_write"
    HISTORY_READ = "history_read"
    HISTORY_WRITE = "history_write"
    MODEL_INFO = "model_info"
    MODEL_PREDICT = "model_predict"
    ADMIN_READ = "admin_read"
    ADMIN_WRITE = "admin_write"
