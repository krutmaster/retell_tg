import psycopg2
from psycopg2 import sql
from secret import dbname, user, password, host, port


# Функция для подключения к базе данных
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


# Функция для выполнения SQL-запроса
def execute_query(conn, cursor, query, params=None):
    try:
        # Выполняем SQL-запрос
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Если это SELECT-запрос, то возвращаем результат
        if query.strip().lower().startswith('select'):
            result = cursor.fetchall()
            return result

        # Фиксируем изменения (для запросов INSERT/UPDATE/DELETE)
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None

    finally:
        # Закрываем курсор и соединение
        cursor.close()
        conn.close()
