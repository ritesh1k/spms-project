import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, "..", ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_USER = os.environ.get("MYSQL_USER", "student_user")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "Student12345")
    MYSQL_DB = os.environ.get("MYSQL_DB", "student_performance")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
