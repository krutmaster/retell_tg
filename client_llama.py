from db import connect_to_db, execute_query
from llama import request_to_lamma
from time import sleep



def get_unanswered_text():
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    query = "select id, history from dialog where is_answered = %s limit 1"
    params = ('false',)
    res = execute_query(conn, cursor, query, params)
    return res


def update_dialog_from_llama(dialog_id, text):
    # Подключаемся к базе данных
    conn = connect_to_db()
    # Открываем курсор для выполнения операций с БД
    cursor = conn.cursor()
    query = "update dialog set history = %s, is_answered = %s where id = %s"
    params = (text, 'true', dialog_id)
    execute_query(conn, cursor, query, params)


def main():
    while True:
        text_for_retell = get_unanswered_text()
        if text_for_retell:
            retell, history = request_to_lamma(text_for_retell[0][1], True)
            update_dialog_from_llama(text_for_retell[0][0], str(history))
        sleep(10)


if __name__ == '__main__':
    main()
