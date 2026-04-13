import os
import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host=os.environ.get("SPMS_DB_HOST", "localhost"),
        user=os.environ.get("SPMS_DB_USER", "student_user"),
        password=os.environ.get("SPMS_DB_PASSWORD", "Student12345"),
        database=os.environ.get("SPMS_DB_NAME", "student_performance"),
        charset="utf8mb4",
        use_unicode=True,
    )
