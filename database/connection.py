import mysql.connector

from config.config import Config


def get_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        charset=Config.MYSQL_CHARSET,
        use_unicode=True,
    )


def test_connection():
    connection = None
    try:
        connection = get_connection()
        connection.ping(reconnect=True, attempts=1, delay=0)
        return True
    except Exception:
        return False
    finally:
        if connection is not None:
            connection.close()