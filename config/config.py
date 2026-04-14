import os


def _env(*names, default=None):
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
    return default


class Config:
    SECRET_KEY = _env("SECRET_KEY", default="change-me-in-production")
    MYSQL_HOST = _env("MYSQL_HOST", "SPMS_DB_HOST", default="localhost")
    MYSQL_USER = _env("MYSQL_USER", "SPMS_DB_USER", default="student_user")
    MYSQL_PASSWORD = _env("MYSQL_PASSWORD", "SPMS_DB_PASSWORD", default="Student12345")
    MYSQL_DB = _env("MYSQL_DB", "SPMS_DB_NAME", default="student_performance")
    MYSQL_PORT = int(_env("MYSQL_PORT", "SPMS_DB_PORT", default="3306"))
    MYSQL_CHARSET = "utf8mb4"