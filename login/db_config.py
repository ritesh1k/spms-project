import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="student_user",
        password="student123",   # same password you used in mysql -p
        database="student_performance"
    )
