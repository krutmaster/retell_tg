import psycopg2
import os
from dotenv import load_dotenv


load_dotenv()
dbname = os.getenv('dbname')
user = os.getenv('user')
password = os.getenv('password')
host = os.getenv('host')
port = os.getenv('port')


def connect_to_db():
    # Параметры подключения к базе данных
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    return conn


def execute_query(conn, cursor, query, params=None):
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if query.strip().lower().startswith('select'):
            result = cursor.fetchall()
            return result

        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None

    finally:
        cursor.close()
        conn.close()
